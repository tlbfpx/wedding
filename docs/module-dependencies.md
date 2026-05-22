# 模块依赖关系文档

> **版本**: 现状版 - 基线建档
> **日期**: 2026-05-22
> **说明**: 本文档基于现有代码逆向梳理，反映系统当前实际模块依赖关系。

---

## 1. 依赖关系矩阵

| 模块 | 依赖 | 依赖类型 | 说明 |
|------|------|----------|------|
| auth | users | 同步调用（数据库查询） | 认证时查询 User 表验证用户身份和状态，查询 Role 表获取权限 |
| customers | users | 同步调用（外键引用） | Customer.assigned_sale_id → User.id，FollowUp.sale_id → User.id |
| orders | customers | 同步调用（外键引用） | Order.customer_id → Customer.id |
| orders | users | 同步调用（外键引用） | Order.sale_id → User.id, Order.planner_id → User.id |
| orders | suppliers | 同步调用（外键引用） | OrderItem.supplier_id → Supplier.id |
| events | users | 同步调用（外键引用） | Event.planner_id → User.id, StaffSchedule.staff_id → User.id |
| events | venues | 同步调用（外键引用 + 冲突检测查询） | Event.venue_id → Venue.id，创建/更新活动时查询场地冲突 |
| events | orders | 同步调用（外键引用） | Event.order_id → Order.id（可选关联） |
| suppliers | orders | 同步调用（外键引用） | SupplierEvaluation.order_id → Order.id |
| suppliers | users | 同步调用（外键引用） | SupplierEvaluation.evaluator_id → User.id |
| approvals | orders | 同步调用（外键引用 + 联动操作） | Approval.target_id → Order.id，审批通过后直接修改订单状态或金额 |
| approvals | users | 同步调用（外键引用） | Approval.applicant_id → User.id, Approval.approver_id → User.id |
| dashboard | orders | 同步调用（聚合查询） | 统计订单数、营业额、财务汇总等 |
| dashboard | customers | 同步调用（聚合查询） | 统计客户数、客户转化漏斗 |
| dashboard | events | 同步调用（聚合查询） | 统计排期数、排期热力图 |
| dashboard | suppliers | 同步调用（聚合查询） | 供应商排行 |
| dashboard | users | 同步调用（聚合查询） | 销售排行 |
| users | — | 无外部依赖 | 基础模块，仅依赖自身数据模型 |

### 依赖方向可视化

```
                    auth
                     │
                     ▼
  ┌──────────────── users ◀───────────────────┐
  │         ▲     ▲  ▲  ▲                     │
  │         │     │  │  │                     │
  │    customers  │  │  │                     │
  │         │     │  │  │                     │
  │         ▼     │  │  │                     │
  │       orders──┘  │  │                     │
  │       │  │       │  │                     │
  │       │  ▼       │  │                     │
  │       │ suppliers ┘  │                     │
  │       │              │                     │
  │       ▼              │                     │
  │     approvals ───────┘                     │
  │                                            │
  └──▶ events ──▶ venues                      │
       │                                        │
       └────────────────────────────────────────┘
                   dashboard（只读聚合，依赖所有模块）
```

---

## 2. 跨模块数据流

### 2.1 客户 → 订单

- **流程描述**：销售创建意向订单时，选择已有客户作为订单关联方。订单通过 `customer_id` 外键关联客户。
- **涉及的 API 调用**：
  - 前端 OrderCreate 页面调用 `GET /api/v1/customers` 远程搜索客户
  - 前端调用 `POST /api/v1/orders` 创建订单，请求体中传入 `customer_id`
- **数据流向**：Customer.id → Order.customer_id（外键关联）

### 2.2 订单 → 供应商

- **流程描述**：订单中的订单项可关联供应商，指定该服务项目的提供方。供应商评价通过订单关联。
- **涉及的 API 调用**：
  - 前端 OrderCreate 页面调用 `GET /api/v1/suppliers` 获取供应商列表
  - 前端调用 `POST /api/v1/orders` 创建订单，订单项中传入 `supplier_id`
  - 前端 SupplierDetail 页面调用 `POST /api/v1/suppliers/{id}/evaluations` 添加评价，传入 `order_id`
- **数据流向**：
  - Supplier.id → OrderItem.supplier_id（外键关联）
  - Order.id → SupplierEvaluation.order_id（评价关联）

### 2.3 订单 → 审批

- **流程描述**：折扣低于 9 折需提交折扣审批，取消订单需提交取消审批，退款需提交退款审批。审批通过后自动执行关联操作。
- **涉及的 API 调用**：
  - 前端 OrderDetail 页面调用 `POST /api/v1/approvals` 提交审批，传入 `type` 和 `target_id`（订单 ID）
  - 前端 Approvals 页面调用 `PUT /api/v1/approvals/{id}` 进行审批决策
  - 后端审批通过后自动执行：取消订单（Order.status → cancelled）或退款（Order.paid_amount → 0）
- **数据流向**：
  - Approval 创建：Order.id → Approval.target_id
  - 审批通过联动：Approval 模块直接修改 Order 状态/金额

### 2.4 订单 → 活动

- **流程描述**：一个订单可关联一个活动（一对一），用于将订单执行与排期绑定。
- **涉及的 API 调用**：
  - 前端 EventList 页面调用 `POST /api/v1/events` 创建活动，可传入 `order_id`
- **数据流向**：Order.id → Event.order_id（唯一约束，一对一关系）

### 2.5 活动 → 场地

- **流程描述**：活动通过场地 ID 关联场地。创建或修改活动时，系统自动检测同日同场地的冲突。
- **涉及的 API 调用**：
  - 前端 EventList/EventDetail 页面创建/更新活动时传入 `venue_id`
  - 后端 `_detect_conflicts` 函数查询同日同场地的已有活动
  - 前端 VenueList 页面调用 `GET /api/v1/venues/{id}/availability` 查看场地档期
- **数据流向**：
  - Venue.id → Event.venue_id（外键关联）
  - 冲突检测：Events 模块查询同 Venue 的非 cancelled 活动

### 2.6 活动 → 用户（排班）

- **流程描述**：活动可安排多名员工（摄影师、化妆师等），通过 StaffSchedule 关联。创建活动时检测人员排班冲突。
- **涉及的 API 调用**：
  - 前端 EventDetail 页面调用 `GET /api/v1/events/staff-schedule` 查看排班
  - 后端 `_detect_conflicts` 函数检测同日同员工的排班冲突
- **数据流向**：
  - User.id → StaffSchedule.staff_id（外键关联）
  - User.id → Event.planner_id（策划师关联）

### 2.7 客户 → 用户（销售）

- **流程描述**：客户可指派销售负责跟进。销售可将客户转移给其他销售或回收到公海池。
- **涉及的 API 调用**：
  - 前端 CustomerList 页面调用 `POST /api/v1/customers/{id}/transfer` 转移客户
  - 前端 CustomerList 页面调用 `POST /api/v1/customers/{id}/recycle` 回收客户
  - 前端 CustomerPool 页面调用 `POST /api/v1/customer-pool/{id}/claim` 认领客户
  - 前端转移时调用 `GET /api/v1/users` 获取销售列表
- **数据流向**：
  - User.id → Customer.assigned_sale_id（外键关联）
  - User.id → FollowUp.sale_id（跟进记录关联）

### 2.8 工作台 → 多模块聚合

- **流程描述**：Dashboard 从订单、客户、活动等多个模块聚合统计数据，使用 Redis 缓存（5 分钟过期）。
- **涉及的 API 调用**：
  - 前端 Dashboard 页面调用 `GET /api/v1/dashboard/overview` 获取概览数据
  - 后端 Dashboard 路由聚合查询 Order、Customer、Event 等表
- **数据流向**：只读聚合，不修改任何模块数据

### 2.9 认证 → 用户

- **流程描述**：认证模块依赖 User 和 Role 模型进行身份验证和权限查询。
- **涉及的 API 调用**：
  - `POST /api/v1/auth/login` → 查询 User 表验证用户名密码
  - `GET /api/v1/auth/me` → 查询 User 和 Role 表获取用户信息和权限
  - 认证中间件 `get_current_user` → 从 JWT 提取用户 ID，查询 User 表
- **数据流向**：只读查询，不修改 User 表（登录失败计数存储在 Redis）

---

## 3. 循环依赖检查

### 3.1 模块级依赖图（简化）

```
users ←──── customers
  ▲            │
  │            ▼
  │         orders ←── suppliers（evaluations.order_id）
  │         │  ▲
  │         │  │
  │         ▼  │
  │      approvals
  │
  ├── events ──▶ venues
  │
  └── dashboard（依赖所有模块，仅只读）
```

### 3.2 检查结论

**不存在循环依赖**。分析如下：

| 依赖链 | 方向 | 是否形成环 |
|--------|------|-----------|
| orders → customers → users | 单向 | 否 |
| orders → suppliers → users | 单向 | 否 |
| approvals → orders → users | 单向 | 否 |
| approvals → orders → customers → users | 单向 | 否 |
| events → venues | 单向 | 否 |
| events → orders → ... | 单向 | 否 |
| suppliers → orders → ... | 单向（仅 SupplierEvaluation） | 否 |
| dashboard → 所有模块 | 单向（只读） | 否 |

**说明**：虽然 suppliers 模块通过 `SupplierEvaluation.order_id` 引用了 orders 模块，orders 模块也通过 `OrderItem.supplier_id` 引用了 suppliers 模块，但这属于**数据模型层面的双向外键引用**，不构成模块级的循环依赖——orders 在创建订单项时仅读取 Supplier ID，suppliers 在创建评价时仅读取 Order ID，两者不发生互相调用业务逻辑的情况。

---

## 4. 外部依赖

### 4.1 基础设施依赖

| 依赖 | 类型 | 用途 | 配置位置 |
|------|------|------|---------|
| MySQL 8 | 关系型数据库 | 所有业务数据持久化 | `settings.DATABASE_URL` |
| Redis | 内存数据库 | 登录失败计数、Token 黑名单、Dashboard 缓存 | `settings.REDIS_URL` |
| 本地文件系统 | 文件存储 | 合同文件上传与存储 | `settings.UPLOAD_DIR` |

### 4.2 Python 第三方库

| 依赖 | 用途 |
|------|------|
| fastapi | Web 框架 |
| uvicorn | ASGI 服务器 |
| sqlalchemy[asyncio] | 异步 ORM |
| asyncmy | MySQL 异步驱动 |
| redis | Redis 客户端 |
| pyjwt | JWT Token 生成与验证 |
| bcrypt | 密码哈希 |
| reportlab | 报价单 PDF 生成 |
| pydantic | 数据校验与序列化 |
| python-multipart | 文件上传处理 |

### 4.3 前端第三方依赖

| 依赖 | 用途 |
|------|------|
| vue | 前端框架 |
| naive-ui | UI 组件库 |
| pinia | 状态管理 |
| vue-router | 路由管理 |
| axios | HTTP 客户端 |
| typescript | 类型安全 |
| @vicons/ionicons5 | 图标库 |
