## Context

大型婚庆公司（20+ 员工，覆盖销售/策划/设计/管理四团队）需要从零构建内部管理系统。当前所有业务流程依赖纸质文档、微信沟通和 Excel 表格，存在信息分散、排期冲突、收款遗漏等问题。

这是一个全新项目（greenfield），无遗留系统约束。已有的设计文档（`docs/superpowers/specs/2026-05-21-wedding-management-system-design.md`）定义了完整的数据模型、API 端点和前端页面。

## Goals / Non-Goals

**Goals:**

- 提供 9 个能力模块的完整实现：认证、客户管理、排期管理、订单管理、审批流程、供应商管理、数据看板、系统管理、文件上传
- 前后端分离架构，RESTful API 通信
- RBAC 权限体系（模块级 + 数据级 + 操作级）
- 本地开发友好，最终 Docker Compose 一键部署
- 支撑 20+ 用户并发使用

**Non-Goals:**

- 不做客户端（C 端客户自助平台）
- 不做供应商端（供应商自助系统）
- 不做移动端 App（响应式 Web 适配即可）
- 不做多租户（单公司单实例）
- 不做国际化（仅中文）
- 不做实时通信（WebSocket/SSE），看板数据 5 分钟缓存刷新

## Decisions

### D1. 前后端分离：Vue 3 + FastAPI

**选择**：Vue 3（Vite + Naive UI + Pinia）+ FastAPI（SQLAlchemy 2.0 async + Pydantic v2）

**替代方案**：
- Vue 3 + Django：Django ORM 同步阻塞，FastAPI 原生 async 更适合 I/O 密集场景
- Svelte + FastAPI：Svelte 生态较小，Naive UI 企业级组件库对后台管理系统更成熟
- 单体（FastAPI + Jinja2 + HTMX）：看板等复杂交互难以实现良好的用户体验

**理由**：Vue 3 中文生态成熟，Naive UI 提供完整的后台管理组件（表格/表单/日历/图表），FastAPI 自动生成 OpenAPI 文档便于前后端协作。

### D2. 数据库：MySQL 8 + SQLAlchemy 2.0 async

**选择**：MySQL 8，异步驱动使用 `asyncmy`

**替代方案**：
- PostgreSQL：功能更强，但团队 MySQL 经验更丰富
- SQLite：不支持并发写入，不符合 20+ 用户场景

**理由**：MySQL 在国内部署运维经验丰富，SQLAlchemy 2.0 async + asyncmy 提供非阻塞数据库操作。

### D3. 认证：JWT + Redis 黑名单

**选择**：Access Token 2h + Refresh Token 7d，登出时 Token 加入 Redis 黑名单

**替代方案**：
- Session + Cookie：需要粘性会话或共享存储，Docker 部署复杂
- 纯 JWT 无黑名单：无法即时踢出用户

**理由**：JWT 无状态适合 REST API，Redis 黑名单弥补了 JWT 无法撤销的缺陷，实现简单。

### D4. RBAC 权限：JSON 字段存储

**选择**：Role 表的 permissions 字段存储 JSON，结构为 `{ module: { read/write: scope } }`

**替代方案**：
- 多表关联（role → permission → resource）：过度设计，当前模块和操作类型固定
- 硬编码角色判断：无法灵活调整权限

**理由**：9 个模块、3 层粒度的权限需求用 JSON 足够表达，避免多表 JOIN 查询。Alembic 迁移时可追加字段。

### D5. 公海池：定时任务自动回收

**选择**：后端启动定时任务（APScheduler），每日检查超过 15 天无跟进的客户并自动回收

**替代方案**：
- 纯手动回收：容易遗漏
- Celery 周期任务：引入消息队列，对于单实例部署过重

**理由**：APScheduler 轻量，嵌入 FastAPI 进程内即可，无需额外基础设施。

### D6. 排期冲突检测：应用层校验 + Redis 分布式锁

**选择**：创建/编辑活动时，应用层查询同日同场地/同人员是否已分配，同时用 Redis 锁防止并发写入

**理由**：排期冲突是业务核心痛点，必须在应用层严格校验。Redis 锁防止极端情况下两人同时预订同一场地。

### D7. 文件存储：本地文件系统

**选择**：文件存储在 `uploads/` 目录，Docker 部署时挂载 Volume

**替代方案**：
- MinIO/S3：引入额外依赖，当前仅合同上传场景，体量不需要

**理由**：合同上传是唯一的文件上传场景，频率和量级低，本地文件系统足够。后续需要时可迁移到对象存储。

## Risks / Trade-offs

- **[单实例部署]** → 非高可用，单机故障服务中断。缓解：Docker restart policy + 每日数据库备份
- **[本地文件存储]** → 无法水平扩展，迁移成本。缓解：文件访问统一通过 API 代理，后续替换存储后端不影响前端
- **[JSON 权限字段]** → 无法用 SQL 高效查询权限。缓解：权限校验在应用层中间件完成，不需要 SQL 查询
- **[APScheduler 单进程]** → 定时任务不保证精确时间。缓解：公海池回收对实时性要求低，小时级延迟可接受
- **[看板缓存 5 分钟]** → 数据非实时。缓解：管理层看板对实时性要求不高，刷新即可获取最新数据

## Migration Plan

1. 本地开发：各服务独立运行，MySQL/Redis 可本地安装或 Docker 单独启动
2. 联调测试：Docker Compose 启动完整环境
3. 生产部署：Docker Compose + Nginx 反向代理 + MySQL Volume 挂载 + 每日 mysqldump 备份
4. 数据初始化：首次部署运行 seed 脚本创建管理员账号、默认角色、客户来源等基础数据

## Open Questions

- 是否需要短信/邮件通知（如跟进提醒、审批通知）？当前设计未包含，可作为后续迭代
- 是否需要数据导出功能（Excel 导出客户列表/订单列表）？当前仅支持 PDF 报价单导出
