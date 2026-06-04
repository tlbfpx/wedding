# 2026-06-04 Dashboard 管理层驾驶舱重构

> 变更日期: 2026-06-04
> 需求编号: FR-018
> 变更类型: 重大重构

---

## 1. 变更背景

当前 Dashboard 模块为单文件路由实现，所有查询逻辑内联在 `app/api/dashboard.py` 中，缺乏 Service 层和领域模型。本次重构将 Dashboard 升级为独立的 DDD 模块，提供管理层驾驶舱所需的五大维度数据洞察。

---

## 2. 变更内容

### 2.1 模块结构

新增 `app/dashboard/` 目录，采用标准 DDD 分层：

```
app/dashboard/
├── docs/           # 文档
├── domain/         # 领域层（VO、DTO）
├── application/    # 应用层（Service）
├── infrastructure/ # 基础设施层（缓存）
└── interfaces/     # 接口层（Controller）
```

### 2.2 新增 API

| API | 方法 | 路径 | 功能 |
|-----|------|------|------|
| 经营健康度 | GET | `/api/v1/dashboard/health` | 营收/订单/客单价/签约率/毛利 |
| 现金流 | GET | `/api/v1/dashboard/cashflow` | 现金流入/应收/账龄/周转 |
| 团队效能 | GET | `/api/v1/dashboard/team-efficiency` | 团队对比/转化漏斗/销售排行 |
| 风险预警 | GET | `/api/v1/dashboard/alerts` | 预警列表 |
| 风险预警 | POST | `/api/v1/dashboard/alerts/:id/resolve` | 标记已处理 |
| 决策支撑 | GET | `/api/v1/dashboard/decision-support` | ROI/服务/供应商分析 |

### 2.3 废弃 API

| 旧 API | 替换为 |
|--------|--------|
| `/api/dashboard/overview` | `/api/v1/dashboard/health` |
| `/api/dashboard/sales-ranking` | `/api/v1/dashboard/team-efficiency` |
| `/api/dashboard/conversion-funnel` | `/api/v1/dashboard/team-efficiency` |
| `/api/dashboard/finance-summary` | `/api/v1/dashboard/cashflow` |

废弃 API 保持可用，添加 `Deprecation: true` 响应头。

---

## 3. 技术实现

### 3.1 缓存策略

| 数据类型 | TTL | 失效策略 |
|----------|-----|----------|
| 经营健康度 | 300s | 数据更新时主动失效 |
| 现金流 | 300s | 数据更新时主动失效 |
| 团队效能 | 300s | 数据更新时主动失效 |
| 风险预警 | 60s | 高频刷新 |
| 决策支撑 | 600s | 低频变化 |

### 3.2 权限控制

复用现有 `require_permission` 中间件，根据返回的 `scope` 过滤数据：
- `all`: 无过滤
- `team`: 过滤为本团队
- `own`: 过滤为本人

### 3.3 数据聚合

Dashboard 不引入新的仓储，直接查询 Model 或调用现有 Service：
- Order, Customer, User, Event, Payment 等模型直接查询
- Finance 模块数据可选调用其 Service

---

## 4. 影响范围

### 4.1 后端影响

- 新增 `app/dashboard/` 模块
- 保留 `app/api/dashboard.py`（兼容期）
- 无数据库变更

### 4.2 前端影响

- 新增 `src/api/dashboard.ts` 方法
- 重构 `src/views/Dashboard.vue` 页面
- 旧 API 调用逐步迁移

---

## 5. 兼容性保证

- 旧 API `/api/dashboard/*` 保持可用
- 新 API `/api/v1/dashboard/*` 并行运行
- 建议过渡期 6 个月后移除旧 API

---

## 6. 后续工作

- [ ] 各功能详细设计文档（feature-*.md）
- [ ] 接口契约文档（contracts.md）
- [ ] Service 层实现
- [ ] Controller 层实现
- [ ] 前端页面重构
- [ ] 集成测试
