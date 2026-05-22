# 婚庆管理系统 - 架构设计文档

> **版本**: 现状版 - 基线建档
> **日期**: 2026-05-22
> **说明**: 本文档基于现有代码逆向梳理，反映系统当前实际架构状态。

---

## 1. 系统概述

### 1.1 系统定位

婚庆管理系统是一套面向婚庆公司的全流程业务管理平台，涵盖客户获客与跟进、排期调度、场地管理、订单与合同、供应商协作、审批流程、员工权限管理等核心业务场景。

### 1.2 技术栈总览

| 层级 | 技术 | 版本/说明 |
|------|------|-----------|
| 前端框架 | Vue 3（Composition API + `<script setup>`） | ^3.5.34 |
| 前端 UI 库 | Naive UI | ^2.44.1 |
| 前端构建 | Vite | ^8.0.12 |
| 前端状态管理 | Pinia | ^3.0.4 |
| 前端路由 | Vue Router 4 | ^4.6.4 |
| 前端 HTTP | Axios | ^1.16.1 |
| 前端语言 | TypeScript | ~6.0.2 |
| 后端框架 | FastAPI | Python 异步 Web 框架 |
| 后端 ORM | SQLAlchemy 2.0（async） | 异步 ORM |
| 数据库 | MySQL 8 | asyncmy 驱动 |
| 缓存 | Redis | 登录锁定、Token 黑名单、Dashboard 缓存 |
| 认证 | JWT（PyJWT） | Access Token + Refresh Token 双令牌 |
| 密码加密 | bcrypt | 用户密码哈希存储 |
| PDF 生成 | reportlab | 报价单 PDF 动态生成 |

### 1.3 部署架构

```
┌──────────────────────────────────────────────────┐
│                  前端（Vue 3 SPA）                │
│              wedding-frontend/                    │
│         Vite 构建 → 静态资源部署                   │
└────────────────────┬─────────────────────────────┘
                     │ HTTP REST API（/api/v1/*）
                     │ JWT Bearer Token 认证
┌────────────────────▼─────────────────────────────┐
│                后端（FastAPI）                     │
│              wedding-backend/                     │
│         ASGI 服务（uvicorn）                       │
├──────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────────────┐  │
│  │ MySQL 8 │  │  Redis  │  │ 本地文件系统     │  │
│  │ 业务数据 │  │ 缓存/锁 │  │ 合同文件存储     │  │
│  └─────────┘  └─────────┘  └─────────────────┘  │
└──────────────────────────────────────────────────┘
```

---

## 2. 系统架构

### 2.1 分层架构

```
┌───────────────────────────────────────────────────────────────┐
│                        前端（Vue 3 SPA）                       │
│  views/ ← stores/ ← api/ ← axios（请求拦截器 + 响应拦截器）    │
└───────────────────────────┬───────────────────────────────────┘
                            │ REST API（/api/v1/*）
┌───────────────────────────▼───────────────────────────────────┐
│                        API 层（FastAPI 路由）                   │
│  api/auth.py, api/customers.py, api/orders.py, api/events.py, │
│  api/venues.py, api/suppliers.py, api/users.py,               │
│  api/approvals.py, api/dashboard.py                           │
├───────────────────────────────────────────────────────────────┤
│                        中间件层                                │
│  middleware/auth.py（身份认证 + 权限检查）                      │
│  middleware/log_operation.py（操作日志记录）                    │
├───────────────────────────────────────────────────────────────┤
│                        业务层（路由内联）                       │
│  业务逻辑直接写在 API 路由处理函数中，未封装独立 Service 层     │
├───────────────────────────────────────────────────────────────┤
│                        数据层                                  │
│  models/（SQLAlchemy ORM 模型）                                │
│  utils/auth.py（Token 工具）                                   │
│  database.py（数据库连接）                                     │
├───────────────────────────────────────────────────────────────┤
│                        基础设施                                │
│  MySQL 8（业务数据）+ Redis（缓存/锁定）+ 文件系统（合同存储）  │
└───────────────────────────────────────────────────────────────┘
```

### 2.2 技术选型说明

| 决策 | 选型 | 理由 |
|------|------|------|
| 前后端分离 | REST API | 前后端独立开发、部署，前端 SPA 体验 |
| 异步框架 | FastAPI + async SQLAlchemy | 高并发 I/O 场景（数据库查询、文件操作） |
| ORM 异步 | SQLAlchemy 2.0 async | 类型安全、异步支持、成熟生态 |
| 双 Token 认证 | Access + Refresh Token | 安全性与可用性平衡 |
| 操作日志 | 中间件自动记录 | 全局审计，减少业务代码侵入 |

---

## 3. 模块划分

### 3.1 模块列表

| 模块 | 职责 | API 文件 | Model 文件 | 前端页面 |
|------|------|----------|-----------|----------|
| auth | 用户认证（登录/登出/Token 刷新） | `api/auth.py` | 复用 `models/user.py` | Login |
| customers | 客户管理、跟进记录、公海池 | `api/customers.py` | `models/customer.py` | CustomerList, CustomerDetail, CustomerPool |
| orders | 订单管理、付款、合同、PDF 生成 | `api/orders.py` | `models/order.py` | Orders, OrderCreate, OrderDetail |
| events | 活动排期、资源管理、冲突检测 | `api/events.py` | `models/event.py` | EventList, EventDetail |
| venues | 场地管理、可用性查询 | `api/venues.py` | 复用 `models/event.py`（Venue） | VenueList |
| suppliers | 供应商管理、服务项目、评价 | `api/suppliers.py` | `models/supplier.py` | SupplierList, SupplierDetail |
| users | 员工管理、角色权限、操作日志 | `api/users.py` | `models/user.py`, `models/log.py` | UserList, RoleList, OperationLogs |
| approvals | 审批管理（折扣/退款/取消） | `api/approvals.py` | 复用 `models/order.py`（Approval） | Approvals |
| dashboard | 工作台数据概览 | `api/dashboard.py` | 聚合查询 | Dashboard |

### 3.2 模块间调用关系

```
                    ┌─────────┐
                    │  auth   │ ← 所有需要认证的 API
                    └────┬────┘
                         │ 依赖
                         ▼
┌─────────┐       ┌─────────┐       ┌───────────┐
│customers│──────▶│  users  │◀──────│  orders   │
└────┬────┘       └────┬────┘       └─────┬─────┘
     │                 │                   │
     │                 │            ┌──────▼──────┐
     │                 │            │  approvals  │
     │                 │            └─────────────┘
     │                 │                   │
     ▼                 ▼                   ▼
┌─────────┐       ┌─────────┐       ┌───────────┐
│ orders  │──────▶│ events  │◀──────│  venues   │
└────┬────┘       └────┬────┘       └───────────┘
     │                 │
     ▼                 ▼
┌───────────┐    ┌───────────┐
│ suppliers │    │dashboard  │
└───────────┘    └───────────┘
```

**说明**：
- `users` 是基础支撑模块，几乎所有模块通过外键引用用户
- `orders` 是核心业务模块，与 customers、suppliers、users、events、approvals 均有关联
- `approvals` 与 `orders` 强耦合，审批目标为订单
- `venues` 通过 `events` 间接被使用（Event.venue_id → Venue）
- `dashboard` 为只读聚合模块，不拥有独立数据模型

---

## 4. 领域模型

### 4.1 核心聚合/实体

| 实体 | 所属模块 | 关键字段 | 关联关系 |
|------|----------|----------|----------|
| Customer | customers | name, phone(唯一), status, budget_range, wedding_date, assigned_sale_id, recycled_at | N:1 User(sale), N:1 CustomerSource, 1:N FollowUp, 1:N Order |
| FollowUp | customers | customer_id, sale_id, type, content, next_follow_at | N:1 Customer, N:1 User(sale) |
| CustomerSource | customers | name(唯一) | 1:N Customer |
| Order | orders | order_no(唯一), customer_id, planner_id, sale_id, status, total_amount, paid_amount, discount | N:1 Customer, N:1 User(sale), N:1 User(planner), 1:N OrderItem, 1:N Payment, 0..1 Contract, 1:N Approval, 0..1 Event |
| OrderItem | orders | order_id, type, name, quantity, unit_price, amount, supplier_id | N:1 Order, N:1 Supplier |
| Payment | orders | order_id, amount, method, status, paid_at | N:1 Order |
| Contract | orders | order_id, file_url, status, signed_at | 1:1 Order |
| Approval | orders | type, target_id, applicant_id, approver_id, status, reason | N:1 Order, N:1 User(applicant), N:1 User(approver) |
| Event | events | order_id(唯一), title, date, venue_id, planner_id, status | 0..1:1 Order, N:1 Venue, N:1 User(planner), 1:N EventResource, 1:N StaffSchedule |
| EventResource | events | event_id, resource_type, resource_id, quantity | N:1 Event |
| StaffSchedule | events | staff_id, event_id, role, date, status | N:1 Event, N:1 User(staff) |
| Venue | events | name(唯一), address, capacity, price | 1:N Event |
| Supplier | suppliers | name, type, cooperation_status, rating | 1:N SupplierService, 1:N SupplierEvaluation, 1:N OrderItem |
| SupplierService | suppliers | supplier_id, service_name, price, unit | N:1 Supplier |
| SupplierEvaluation | suppliers | supplier_id, order_id, rating, content, evaluator_id | N:1 Supplier, N:1 Order, N:1 User(evaluator) |
| User | users | username(唯一), password_hash, name, role_id, team, status | N:1 Role |
| Role | users | name(唯一), permissions(JSON) | 1:N User |
| OperationLog | users | user_id, module, action, target, detail, ip | N:1 User |

### 4.2 实体关系图

```
CustomerSource (1) ──── (N) Customer (N) ──── (1) User (assigned_sale)
                                 │
                                 ├── (N) FollowUp ──── (1) User (sale)
                                 │
                                 └──── (1) ──── (N) Order
                                                    ├── N:1 User (sale)
                                                    ├── N:1 User (planner)
                                                    ├── (N) OrderItem ──── N:1 Supplier
                                                    ├── (N) Payment
                                                    ├── (0..1) Contract
                                                    ├── (N) Approval ──── N:1 User (applicant)
                                                    │                  └── N:1 User (approver)
                                                    └── (0..1) Event ──── N:1 Venue
                                                                         ├── N:1 User (planner)
                                                                         ├── (N) EventResource
                                                                         └── (N) StaffSchedule ──── N:1 User (staff)

Supplier (1) ──── (N) SupplierService
         │
         └──── (N) SupplierEvaluation ──── N:1 Order
                                           └── N:1 User (evaluator)

User ──── N:1 Role

OperationLog ──── N:1 User
```

---

## 5. API 设计总览

| 模块 | 方法 | 路径 | 用途 |
|------|------|------|------|
| **auth** | POST | `/api/v1/auth/login` | 用户登录 |
| auth | POST | `/api/v1/auth/refresh` | 刷新令牌 |
| auth | POST | `/api/v1/auth/logout` | 登出 |
| auth | GET | `/api/v1/auth/me` | 获取当前用户信息及权限 |
| **customers** | GET | `/api/v1/customers` | 客户列表（分页、筛选） |
| customers | GET | `/api/v1/customers/{id}` | 客户详情（含跟进记录） |
| customers | POST | `/api/v1/customers` | 创建客户 |
| customers | PUT | `/api/v1/customers/{id}` | 更新客户（乐观锁） |
| customers | POST | `/api/v1/customers/{id}/follow-ups` | 新增跟进记录 |
| customers | POST | `/api/v1/customers/{id}/transfer` | 转移客户 |
| customers | POST | `/api/v1/customers/{id}/recycle` | 回收客户到公海池 |
| customers | GET | `/api/v1/customer-pool` | 公海池列表 |
| customers | POST | `/api/v1/customer-pool/{id}/claim` | 认领公海池客户 |
| **orders** | GET | `/api/v1/orders` | 订单列表（分页、筛选） |
| orders | GET | `/api/v1/orders/{id}` | 订单详情（含项目、付款、合同） |
| orders | POST | `/api/v1/orders` | 创建订单（含订单项） |
| orders | PUT | `/api/v1/orders/{id}` | 更新订单（仅意向状态可改） |
| orders | PUT | `/api/v1/orders/{id}/status` | 订单状态流转 |
| orders | POST | `/api/v1/orders/{id}/payments` | 登记付款 |
| orders | POST | `/api/v1/orders/{id}/contract` | 上传合同文件 |
| orders | GET | `/api/v1/orders/{id}/quote-pdf` | 生成报价单 PDF |
| **events** | GET | `/api/v1/events` | 活动列表（日历视图数据） |
| events | GET | `/api/v1/events/{id}` | 活动详情（含资源+排班） |
| events | POST | `/api/v1/events` | 创建活动（含冲突检测） |
| events | PUT | `/api/v1/events/{id}` | 更新活动 |
| events | GET | `/api/v1/events/staff-schedule` | 员工排班查询 |
| events | GET | `/api/v1/events/conflicts` | 冲突检测 |
| events | GET | `/api/v1/events/{id}/resources` | 活动资源列表 |
| events | POST | `/api/v1/events/{id}/resources` | 添加活动资源 |
| events | DELETE | `/api/v1/events/{id}/resources/{rid}` | 移除活动资源 |
| **venues** | GET | `/api/v1/venues` | 场地列表 |
| venues | POST | `/api/v1/venues` | 创建场地 |
| venues | PUT | `/api/v1/venues/{id}` | 更新场地 |
| venues | GET | `/api/v1/venues/{id}/availability` | 场地可用性查询 |
| **suppliers** | GET | `/api/v1/suppliers` | 供应商列表 |
| suppliers | GET | `/api/v1/suppliers/{id}` | 供应商详情（含服务+评价） |
| suppliers | POST | `/api/v1/suppliers` | 创建供应商 |
| suppliers | PUT | `/api/v1/suppliers/{id}` | 更新供应商 |
| suppliers | GET | `/api/v1/suppliers/{id}/services` | 供应商服务列表 |
| suppliers | POST | `/api/v1/suppliers/{id}/services` | 添加服务项目 |
| suppliers | PUT | `/api/v1/suppliers/{id}/services/{sid}` | 更新服务项目 |
| suppliers | GET | `/api/v1/suppliers/{id}/evaluations` | 供应商评价列表 |
| suppliers | POST | `/api/v1/suppliers/{id}/evaluations` | 添加供应商评价 |
| **users** | GET | `/api/v1/users` | 员工列表 |
| users | POST | `/api/v1/users` | 创建员工 |
| users | PUT | `/api/v1/users/{id}` | 更新员工 |
| users | GET | `/api/v1/users/roles` | 角色列表 |
| users | PUT | `/api/v1/users/roles/{id}` | 更新角色权限 |
| users | GET | `/api/v1/users/operation-logs` | 操作日志列表 |
| **approvals** | GET | `/api/v1/approvals` | 审批列表 |
| approvals | POST | `/api/v1/approvals` | 提交审批 |
| approvals | PUT | `/api/v1/approvals/{id}` | 审批决策（通过/驳回） |
| **dashboard** | GET | `/api/v1/dashboard/overview` | 概览数据 |
| dashboard | GET | `/api/v1/dashboard/sales-ranking` | 销售排行 |
| dashboard | GET | `/api/v1/dashboard/conversion-funnel` | 客户转化漏斗 |
| dashboard | GET | `/api/v1/dashboard/finance-summary` | 财务汇总 |
| dashboard | GET | `/api/v1/dashboard/schedule-heatmap` | 排期热力图 |
| dashboard | GET | `/api/v1/dashboard/supplier-ranking` | 供应商排行 |

---

## 6. 事件驱动设计

### 6.1 现有模块间通信方式

当前系统**未实现显式的领域事件机制**，所有模块间通信均为**同步调用**（数据库外键关联 + 直接数据访问）：

| 通信方式 | 使用场景 | 示例 |
|----------|----------|------|
| 数据库外键关联 | 数据实体间的引用关系 | Order.customer_id → Customer.id |
| 直接数据库查询 | 跨模块数据读取 | Dashboard 查询 Order/Event/Customer 聚合统计 |
| API 路由内联逻辑 | 跨模块业务联动 | Approval 通过后直接修改 Order 状态 |
| 中间件 | 全局横切关注点 | log_operation 记录所有写操作日志 |

### 6.2 跨模块业务联动

以下为当前系统中存在的跨模块业务联动点（均为同步、内联实现）：

| 联动场景 | 触发模块 | 目标模块 | 联动行为 |
|----------|---------|---------|---------|
| 首次跟进 → 客户状态变更 | customers | customers（内部） | Customer.status: potential → following |
| 创建订单 → 关联客户 | orders | customers | Order 通过 customer_id 外键关联 Customer |
| 订单项 → 关联供应商 | orders | suppliers | OrderItem 通过 supplier_id 外键关联 Supplier |
| 审批通过 → 取消订单 | approvals | orders | Order.status → cancelled |
| 审批通过 → 退款 | approvals | orders | Order.paid_amount → 0 |
| 活动创建 → 场地冲突检测 | events | venues | 查询同日同场地是否已有活动 |
| 活动创建 → 人员冲突检测 | events | users | 查询同日同员工是否已有排班 |
| 供应商评价 → 评分更新 | suppliers | suppliers（内部） | Supplier.rating 自动重算平均值 |
| 工作台 → 多模块聚合查询 | dashboard | orders, customers, events | 跨模块聚合统计数据 |

### 6.3 潜在的事件驱动改造候选

各模块契约文档中标注的隐含事件：

| 模块 | 隐含事件 | 触发时机 | 潜在消费方 |
|------|---------|---------|-----------|
| customers | CustomerCreated | 创建客户时 | Dashboard |
| customers | CustomerStatusChanged | 客户状态变更时 | Dashboard |
| customers | CustomerRecycled / CustomerClaimed | 公海池操作时 | Dashboard |
| orders | OrderCreated | 创建订单时 | Customers（更新客户状态） |
| orders | OrderStatusChanged | 订单状态流转时 | Customers、Dashboard |
| orders | PaymentRecorded | 记录付款时 | Dashboard |
| suppliers | SupplierEvaluated | 添加供应商评价时 | Dashboard |

---

## 7. 数据存储

### 7.1 数据库表结构概览

| 表名 | 所属模型文件 | 说明 | 关键索引 |
|------|------------|------|---------|
| users | `models/user.py` | 用户/员工 | username (UNIQUE) |
| roles | `models/user.py` | 角色 | name (UNIQUE) |
| operation_logs | `models/log.py` | 操作日志 | user_id, module, created_at |
| customers | `models/customer.py` | 客户 | phone (UNIQUE), assigned_sale_id, status |
| follow_ups | `models/customer.py` | 跟进记录 | customer_id, sale_id |
| customer_sources | `models/customer.py` | 客户来源字典 | name (UNIQUE) |
| orders | `models/order.py` | 订单 | order_no (UNIQUE), customer_id, sale_id, status |
| order_items | `models/order.py` | 订单项 | order_id, supplier_id |
| payments | `models/order.py` | 付款记录 | order_id |
| contracts | `models/order.py` | 合同 | order_id |
| approvals | `models/order.py` | 审批 | target_id, applicant_id, status |
| events | `models/event.py` | 活动/排期 | order_id (UNIQUE), venue_id, planner_id, date |
| event_resources | `models/event.py` | 活动资源 | event_id |
| staff_schedules | `models/event.py` | 人员排班 | staff_id, event_id, date |
| venues | `models/event.py` | 场地 | name (UNIQUE) |
| suppliers | `models/supplier.py` | 供应商 | type, cooperation_status |
| supplier_services | `models/supplier.py` | 供应商服务 | supplier_id |
| supplier_evaluations | `models/supplier.py` | 供应商评价 | supplier_id, order_id |

### 7.2 特殊存储（Redis）

| Key 模式 | 数据类型 | TTL | 用途 |
|----------|---------|-----|------|
| `login:fail:<username>` | string(int) | 1800s（30分钟） | 登录失败计数，连续 5 次锁定 |
| `jwt:blacklist:<token>` | string | - | Token 黑名单（登出失效，当前未完全实现） |
| Dashboard 缓存 key | string(JSON) | 300s（5分钟） | Dashboard 概览数据缓存 |

### 7.3 文件存储

| 类型 | 存储路径 | 说明 |
|------|---------|------|
| 合同文件 | `{UPLOAD_DIR}/contracts/{order_id}_{timestamp}_{filename}` | 本地文件系统，通过配置 `settings.UPLOAD_DIR` 指定 |

---

## 8. 安全设计

### 8.1 认证机制

| 机制 | 说明 |
|------|------|
| 认证协议 | JWT（JSON Web Token），HS256 签名 |
| Token 类型 | Access Token（短期）+ Refresh Token（长期）双令牌机制 |
| Token 传输 | HTTP 请求头 `Authorization: Bearer {access_token}` |
| 密码存储 | bcrypt 哈希，永不明文存储 |
| 账户锁定 | 连续登录失败 5 次后锁定 30 分钟（Redis 计数） |
| Token 刷新 | Access Token 过期后使用 Refresh Token 换取新 Access Token |
| 登出 | Token 黑名单机制（当前未完全实现） |
| 前端存储 | Token 存储在 localStorage，Axios 拦截器自动注入 |

### 8.2 权限模型（RBAC）

| 概念 | 说明 |
|------|------|
| 角色（Role） | 权限的集合，每个用户绑定一个角色 |
| 权限格式 | 字典格式：`{module: {action: scope}}`，如 `{"crm": {"view": "all", "edit": "own"}}` |
| 权限范围 | `"none"`（无权限）、`"all"`（全部）、`"own"`（仅自己的） |
| 权限检查 | `require_permission(module, action)` 中间件，检查当前用户角色权限 |
| 模块映射 | 内部模块名 → 前端模块名（如 `crm` → `customers`、`schedule` → `events`） |

### 8.3 操作审计

| 机制 | 说明 |
|------|------|
| 日志记录 | `log_operation` 中间件自动记录所有写操作（POST/PUT/DELETE） |
| 日志内容 | 操作人、模块、操作类型、目标路径、操作详情(JSON)、客户端 IP、操作时间 |
| 日志查询 | 支持按操作人、模块、操作类型、日期范围筛选 |
