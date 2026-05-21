## 1. 后端项目初始化

- [x] 1.1 初始化 wedding-backend 项目：创建 FastAPI 应用骨架，配置 CORS、异常处理器、日志
- [x] 1.2 配置 SQLAlchemy 2.0 async + asyncmy 连接 MySQL，创建 database.py（引擎/Session）
- [x] 1.3 配置 Alembic 数据库迁移，执行初始迁移
- [x] 1.4 配置 Redis 连接（aioredis），封装缓存工具函数
- [x] 1.5 创建 requirements.txt（fastapi, uvicorn, sqlalchemy, asyncmy, alembic, pydantic, python-jose, bcrypt, aioredis, apscheduler, python-multipart, reportlab）
- [x] 1.6 创建 .env 配置管理（数据库 URL、Redis URL、JWT Secret、文件上传路径等）

## 2. 公共基础模块

- [x] 2.1 实现 User / Role ORM 模型及 Alembic 迁移
- [x] 2.2 实现 OperationLog ORM 模型及中间件（自动记录 POST/PUT/DELETE 请求）
- [x] 2.3 实现统一分页响应模型（items, total, page, page_size, total_pages）
- [x] 2.4 实现统一错误响应格式（error.code, error.message, error.details）
- [x] 2.5 实现乐观锁工具（updated_at 比对，返回 409 on conflict）
- [x] 2.6 创建 seed 脚本：admin 用户、7 个角色及权限、6 个客户来源

## 3. 认证模块（auth）

- [x] 3.1 实现 JWT 工具函数：生成 access token (2h) 和 refresh token (7d)
- [x] 3.2 实现 `/api/v1/auth/login`：验证用户名密码，检查账户锁定（5 次失败锁 30 分钟）
- [x] 3.3 实现 `/api/v1/auth/refresh`：刷新 access token
- [x] 3.4 实现 `/api/v1/auth/logout`：Token 加入 Redis 黑名单
- [x] 3.5 实现 `/api/v1/auth/me`：返回当前用户信息及权限
- [x] 3.6 实现认证中间件：校验 JWT，检查黑名单，注入当前用户到请求上下文
- [x] 3.7 实现权限中间件：根据 Role.permissions JSON 校验模块级/数据级/操作级权限
- [x] 3.8 编写认证模块单元测试

## 4. 客户管理模块（customer-management）

- [x] 4.1 实现 Customer / FollowUp / CustomerSource ORM 模型及迁移
- [x] 4.2 实现 Customer Pydantic schemas（创建/更新/响应/列表）
- [x] 4.3 实现 `POST /api/v1/customers`：创建客户，phone 唯一性校验
- [x] 4.4 实现 `GET /api/v1/customers`：分页列表，支持 keyword/status/source_id/assigned_sale_id/日期筛选
- [x] 4.5 实现 `GET /api/v1/customers/{id}`：详情 + 最近 10 条跟进记录
- [x] 4.6 实现 `PUT /api/v1/customers/{id}`：编辑客户，乐观锁
- [x] 4.7 实现 `POST /api/v1/customers/{id}/follow-ups`：新增跟进记录
- [x] 4.8 实现 `POST /api/v1/customers/{id}/transfer`：客户转移
- [x] 4.9 实现公海池：`POST recycle`、`GET customer-pool`、`POST claim`
- [x] 4.10 实现 APScheduler 定时任务：每日检查 15 天无跟进客户自动回收
- [x] 4.11 实现数据级权限过滤：sale 看 own，主管看 all，策划 read-only
- [x] 4.12 编写客户管理模块单元测试

## 5. 供应商管理模块（supplier-management）

- [x] 5.1 实现 Supplier / SupplierService / SupplierEvaluation ORM 模型及迁移
- [x] 5.2 实现供应商 Pydantic schemas
- [x] 5.3 实现供应商 CRUD（`GET/POST/PUT /api/v1/suppliers`），筛选 type/status/keyword/rating
- [x] 5.4 实现供应商详情（含服务项目 + 最近 5 条评价）
- [x] 5.5 实现服务报价管理（`GET/POST/PUT /api/v1/suppliers/{id}/services`）
- [x] 5.6 实现供应商评价（`POST /api/v1/suppliers/{id}/evaluations`），自动重算 rating 均值
- [x] 5.7 编写供应商管理模块单元测试

## 6. 订单管理模块（order-management）

- [x] 6.1 实现 Order / OrderItem / Payment / Contract / Approval ORM 模型及迁移
- [x] 6.2 实现订单 Pydantic schemas
- [x] 6.3 实现订单号自动生成（WD + 日期 + 序列号）
- [x] 6.4 实现 `POST /api/v1/orders`：创建订单，自动计算 total_amount
- [x] 6.5 实现 `GET /api/v1/orders`：分页列表，筛选 status/sale_id/planner_id/keyword/日期
- [x] 6.6 实现 `GET /api/v1/orders/{id}`：详情含 items + payments + contract
- [x] 6.7 实现 `PUT /api/v1/orders/{id}`：编辑订单（仅 intention 状态可编辑）
- [x] 6.8 实现 `PUT /api/v1/orders/{id}/status`：状态流转校验，signed 后不可逆向
- [x] 6.9 实现收款登记（`POST /api/v1/orders/{id}/payments`），校验不超过 total
- [x] 6.10 实现报价单 PDF 导出（`GET /api/v1/orders/{id}/quote-pdf`），使用 reportlab
- [x] 6.11 实现折扣审批触发：discount < 0.90 自动创建 Approval
- [x] 6.12 实现数据级权限过滤：sale 看 own，主管看 all
- [x] 6.13 编写订单管理模块单元测试

## 7. 审批流程模块（approval-workflow）

- [x] 7.1 实现 `GET /api/v1/approvals`：审批列表，筛选 status/type/applicant_id
- [x] 7.2 实现 `POST /api/v1/approvals`：手动发起审批
- [x] 7.3 实现 `PUT /api/v1/approvals/{id}`：审批操作（approve/reject），执行关联动作
- [x] 7.4 审批通过后自动执行：折扣生效/退款确认/订单取消
- [x] 7.5 编写审批流程模块单元测试

## 8. 排期管理模块（schedule-management）

- [x] 8.1 实现 Event / EventResource / StaffSchedule / Venue ORM 模型及迁移
- [x] 8.2 实现排期 Pydantic schemas
- [x] 8.3 实现场地 CRUD（`GET/POST/PUT /api/v1/venues`）
- [x] 8.4 实现场地档期查询（`GET /api/v1/venues/{id}/availability`）
- [x] 8.5 实现活动 CRUD（`GET/POST/PUT /api/v1/events`），按月/日期范围查询
- [x] 8.6 实现冲突检测：同场地同日期、同人员同日期，编辑时排除自身
- [x] 8.7 实现 Redis 分布式锁：创建/编辑活动时锁定 venue_id + date
- [x] 8.8 实现资源分配（`POST/DELETE /api/v1/events/{id}/resources`）
- [x] 8.9 实现人员排班查询（`GET /api/v1/staff-schedule`）
- [x] 8.10 实现独立冲突查询端点（`GET /api/v1/conflicts`）
- [x] 8.11 编写排期管理模块单元测试

## 9. 文件上传模块（file-upload）

- [x] 9.1 实现文件上传端点（`POST /api/v1/orders/{id}/contract`），校验类型和大小
- [x] 9.2 实现文件存储到 `uploads/contracts/{order_id}/` 目录
- [x] 9.3 实现文件访问代理（需认证），通过 API 返回文件流
- [x] 9.4 编写文件上传模块单元测试

## 10. 数据看板模块（dashboard）

- [x] 10.1 实现 `GET /api/v1/dashboard/overview`：订单量/营业额/待跟进/排期数，支持 period 参数
- [x] 10.2 实现 `GET /api/v1/dashboard/sales-ranking`：销售排行（个人/团队）
- [x] 10.3 实现 `GET /api/v1/dashboard/conversion-funnel`：客户转化漏斗
- [x] 10.4 实现 `GET /api/v1/dashboard/finance-summary`：应收/已收/逾期统计
- [x] 10.5 实现 `GET /api/v1/dashboard/schedule-heatmap`：排期热力图（每日活动数）
- [x] 10.6 实现 `GET /api/v1/dashboard/supplier-ranking`：供应商满意度排名
- [x] 10.7 实现 Redis 缓存（5 分钟 TTL），按 endpoint + 参数生成 cache key
- [x] 10.8 实现看板数据级权限：admin 全部，主管本团队
- [x] 10.9 编写数据看板模块单元测试

## 11. 系统管理模块（system-management）

- [x] 11.1 实现员工管理（`GET/POST/PUT /api/v1/users`），密码 bcrypt 加密
- [x] 11.2 实现角色管理（`GET/PUT /api/v1/roles`），permissions JSON 校验
- [x] 11.3 实现操作日志查询（`GET /api/v1/operation-logs`）
- [x] 11.4 编写系统管理模块单元测试

## 12. 前端项目初始化

- [x] 12.1 使用 Vite 初始化 Vue 3 + TypeScript 项目
- [x] 12.2 安装并配置 Naive UI 组件库
- [x] 12.3 配置 Pinia 状态管理（auth store）
- [x] 12.4 配置 Vue Router + 路由权限守卫
- [x] 12.5 配置 Axios 实例：base URL、Token 拦截器、刷新 Token 逻辑、错误处理
- [x] 12.6 创建布局组件（MainLayout：侧边栏 + 顶栏 + 内容区）

## 13. 前端 — 登录页

- [x] 13.1 实现登录页面（用户名/密码表单 + 错误提示）
- [x] 13.2 实现 Token 存储（LocalStorage + HttpOnly Cookie）和自动刷新

## 14. 前端 — 工作台（Dashboard）

- [x] 14.1 实现工作台页面：统计卡片（订单/营业额/待跟进/排期）
- [x] 14.2 实现待办事项列表（收款/跟进/审批/执行提醒）
- [x] 14.3 实现近期排期展示

## 15. 前端 — 客户管理

- [x] 15.1 实现客户列表页（表格 + 筛选 + 分页）
- [x] 15.2 实现客户新增/编辑表单（Modal 或独立页面）
- [x] 15.3 实现客户详情页（基本信息 + 跟进时间线）
- [x] 15.4 实现公海池页面（列表 + 认领操作）
- [x] 15.5 实现客户转移功能（选择目标销售）

## 16. 前端 — 排期管理

- [x] 16.1 实现排期日历页面（月/周/日视图，使用 Naive UI Calendar 或第三方日历组件）
- [x] 16.2 实现活动详情页（时间/场地/人员/资源）
- [x] 16.3 实现新建/编辑活动表单，包含冲突检测提示
- [x] 16.4 实现场地管理页面（列表 + 档期查询）
- [x] 16.5 实现人员排班视图

## 17. 前端 — 订单管理

- [x] 17.1 实现订单列表页（表格 + 多条件筛选 + 状态标签）
- [x] 17.2 实现新建订单页面（选择客户 + 添加服务明细 + 折扣 + 总价计算）
- [x] 17.3 实现订单详情页（基本信息 + 明细 + 收款记录 + 合同）
- [x] 17.4 实现收款登记对话框
- [x] 17.5 实现合同上传功能
- [x] 17.6 实现报价单 PDF 预览/下载
- [x] 17.7 实现订单状态操作按钮（根据当前状态显示可用操作）
- [x] 17.8 实现审批列表和审批操作页面

## 18. 前端 — 供应商管理

- [x] 18.1 实现供应商列表页（筛选类型/状态/评分）
- [x] 18.2 实现供应商详情页（信息 + 服务项目 + 评价列表）
- [x] 18.3 实现供应商新增/编辑表单
- [x] 18.4 实现供应商评价提交功能

## 19. 前端 — 系统管理

- [x] 19.1 实现员工管理页面（列表 + 新增/编辑 + 角色分配）
- [x] 19.2 实现角色权限编辑页面（可视化权限矩阵）
- [x] 19.3 实现操作日志查看页面（筛选 + 分页）

## 20. Docker 部署

- [x] 20.1 编写后端 Dockerfile（Python 基础镜像 + 依赖安装）
- [x] 20.2 编写前端 Dockerfile（Node 构建 + Nginx 托管）
- [x] 20.3 编写 nginx.conf（SPA 路由 + API 代理）
- [x] 20.4 编写 docker-compose.yml（frontend + backend + mysql + redis 4 容器）
- [x] 20.5 配置 MySQL 数据持久化（Volume）和 uploads 目录 Volume
- [ ] 20.6 验证完整部署流程（docker-compose up → 登录 → 各模块功能正常）
