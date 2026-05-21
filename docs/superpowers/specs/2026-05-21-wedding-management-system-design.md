# 婚庆公司管理系统 — 设计文档

## 概述

为大型婚庆公司（20+ 人）设计的内部管理系统，涵盖客户管理、排期与资源、订单与财务、供应商管理四大核心业务模块，并配备数据看板供管理层决策使用。

## 技术架构

### 整体架构

前后端分离，RESTful API 通信。

```
Vue 3 SPA ──▶ FastAPI 后端 ──▶ MySQL 8
(Nginx/Vite)   (Uvicorn)       (数据库)
                    │
               Redis (缓存/会话/排期锁)
```

### 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + Naive UI + Pinia + Vue Router + TypeScript |
| 后端 | FastAPI + SQLAlchemy 2.0（异步 ORM）+ Alembic + Pydantic v2 |
| 数据库 | MySQL 8 |
| 缓存 | Redis |
| 认证 | JWT Token |
| 部署 | Docker Compose（前端 Nginx + 后端 Uvicorn + MySQL + Redis） |

### 开发流程

本地开发阶段各服务独立运行（前端 `npm run dev`，后端 `uvicorn`），MySQL 和 Redis 本地安装或单独 Docker 运行。通过 Vite proxy 解决跨域。`.env` 文件管理环境变量。部署时整体 Docker Compose 打包。

## 角色与权限（RBAC）

四种角色，三层权限粒度：模块级（可见性）+ 数据级（本人/本团队/全部）+ 操作级（CRUD）。

| 角色 | CRM | 排期 | 订单 | 供应商 | 看板 | 系统管理 |
|------|-----|------|------|--------|------|----------|
| 管理员 | 全部 | 全部 | 全部 | 全部 | 全部 | 全部 |
| 销售主管 | 全部 | 查看 | 全部 | 查看 | 本团队 | - |
| 销售 | 本人 | 查看 | 本人 | - | - | - |
| 策划主管 | 查看 | 全部 | 查看 | 查看 | 本团队 | - |
| 策划师 | 查看 | 本人 | 查看 | 查看 | - | - |
| 设计主管 | - | 查看 | 查看 | 查看 | 本团队 | - |
| 设计师 | - | 查看 | - | - | - | - |

权限存储：Role 表含 permissions JSON 字段，中间件统一校验。

## 数据模型

### CRM 客户管理模块

**Customer（客户）**
- id, name, phone, gender, source_id, status, budget_range, wedding_date, note
- assigned_sale_id → User
- created_at, updated_at

**FollowUp（跟进记录）**
- id, customer_id → Customer, sale_id → User
- type (电话/微信/面访/其他), content, next_follow_at
- created_at

**CustomerSource（客户来源）**
- id, name (线上咨询/转介绍/线下门店/小红书/抖音/其他)

### 排期与资源管理模块

**Event（活动/婚礼）**
- id, order_id → Order, title, date, start_time, end_time
- venue_id → Venue, status, planner_id → User, note

**EventResource（活动资源分配）**
- id, event_id → Event, resource_type, resource_id, quantity, note

**StaffSchedule（人员排班）**
- id, staff_id → User, event_id → Event, role, date, status

**Venue（场地）**
- id, name, address, capacity, contact, phone, price, note

### 订单与财务模块

**Order（订单）**
- id, order_no (自动生成), customer_id → Customer
- planner_id → User, sale_id → User
- status (意向/已签约/执行中/已完成/已取消)
- total_amount, paid_amount, discount
- note, created_at, updated_at

**OrderItem（订单明细）**
- id, order_id → Order
- type (策划/场地/花艺/摄影/主持/婚车/其他), name
- quantity, unit_price, amount
- supplier_id → Supplier, note

**Payment（收款记录）**
- id, order_id → Order
- amount, method (现金/转账/微信/支付宝/刷卡)
- status (待确认/已确认), paid_at, note

**Contract（合同）**
- id, order_id → Order
- file_url, status, signed_at

**Approval（审批）**
- id, type (折扣审批/退款审批), target_id
- applicant_id → User, approver_id → User
- status (待审批/已通过/已驳回)
- reason, created_at, resolved_at

### 供应商管理模块

**Supplier（供应商）**
- id, name, type (四大金刚/婚车/场地/花艺/摄影摄像/主持/其他)
- contact, phone, address
- cooperation_status (合作中/暂停/黑名单)
- rating, note

**SupplierService（供应商服务/报价）**
- id, supplier_id → Supplier
- service_name, description, price, unit, note

**SupplierEvaluation（供应商评价）**
- id, supplier_id → Supplier, order_id → Order
- rating (1-5), content, evaluator_id → User
- created_at

### 公共实体

**User（用户/员工）**
- id, username, password_hash, name, phone
- role_id → Role, team (销售/策划/设计/管理)
- status (在职/离职)

**Role（角色）**
- id, name, permissions (JSON)

**OperationLog（操作日志）**
- id, user_id → User, module, action, target, detail, ip
- created_at

### 核心关系

- Customer → Order（1:N）
- Order → OrderItem（1:N）
- Order → Event（1:1）
- OrderItem → Supplier（N:1）
- Event → StaffSchedule（1:N）
- Event → EventResource（1:N）
- Customer → FollowUp（1:N）
- Supplier → SupplierEvaluation（1:N）

## API 设计

### 认证

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | /api/auth/login | 登录，返回 JWT |
| POST | /api/auth/logout | 登出 |
| GET | /api/auth/me | 获取当前用户信息 |

### CRM 客户管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /api/customers | 客户列表（筛选：来源/状态/跟进人/时间段） |
| GET | /api/customers/{id} | 客户详情（含跟进时间线） |
| POST | /api/customers | 新增客户 |
| PUT | /api/customers/{id} | 编辑客户 |
| POST | /api/customers/{id}/follow-ups | 新增跟进记录 |
| POST | /api/customers/{id}/transfer | 转移客户给其他销售 |
| POST | /api/customers/{id}/recycle | 回收到公海池 |
| GET | /api/customer-pool | 公海池列表 |
| POST | /api/customer-pool/{id}/claim | 从公海池认领客户 |

### 排期与资源管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /api/events?month=YYYY-MM | 按月获取活动列表 |
| GET | /api/events/{id} | 活动详情 |
| POST | /api/events | 新建活动 |
| PUT | /api/events/{id} | 编辑活动 |
| GET | /api/events/{id}/resources | 活动资源列表 |
| POST | /api/events/{id}/resources | 分配资源 |
| GET | /api/staff-schedule?date= | 人员排班查询 |
| GET | /api/venues | 场地列表 |
| POST | /api/venues | 新增场地 |
| GET | /api/venues/{id}/availability | 场地档期可用性 |
| GET | /api/conflicts?event_id= | 冲突检测 |

### 订单与财务

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /api/orders | 订单列表（筛选：状态/销售/策划/时间段） |
| GET | /api/orders/{id} | 订单详情（含明细+收款记录） |
| POST | /api/orders | 新建订单 |
| PUT | /api/orders/{id} | 编辑订单 |
| PUT | /api/orders/{id}/status | 更新订单状态 |
| POST | /api/orders/{id}/payments | 登记收款 |
| POST | /api/orders/{id}/contract | 上传合同 |
| GET | /api/orders/{id}/quote-pdf | 导出报价单 PDF |
| POST | /api/approvals | 发起审批（折扣/退款） |
| PUT | /api/approvals/{id} | 审批操作（通过/驳回） |

### 供应商管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /api/suppliers | 供应商列表（筛选：类型/合作状态/评分） |
| GET | /api/suppliers/{id} | 供应商详情 |
| POST | /api/suppliers | 新增供应商 |
| PUT | /api/suppliers/{id} | 编辑供应商 |
| GET | /api/suppliers/{id}/services | 供应商服务报价列表 |
| POST | /api/suppliers/{id}/services | 新增服务报价 |
| POST | /api/suppliers/{id}/evaluations | 新增供应商评价 |
| GET | /api/suppliers/{id}/evaluations | 供应商评价列表 |

### 数据看板

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /api/dashboard/overview | 总览数据（订单量/营业额/待跟进/排期） |
| GET | /api/dashboard/sales-ranking | 销售排行（个人/团队） |
| GET | /api/dashboard/conversion-funnel | 客户转化漏斗 |
| GET | /api/dashboard/finance-summary | 收款统计（应收/已收/逾期） |
| GET | /api/dashboard/schedule-heatmap | 排期热力图 |
| GET | /api/dashboard/supplier-ranking | 供应商满意度排名 |

### 系统管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /api/users | 员工列表 |
| POST | /api/users | 新增员工 |
| PUT | /api/users/{id} | 编辑员工 |
| GET | /api/roles | 角色列表 |
| PUT | /api/roles/{id} | 编辑角色权限 |
| GET | /api/operation-logs | 操作日志 |

## 前端设计

### 整体布局

经典后台管理布局：左侧深色导航菜单 + 顶部面包屑/用户栏 + 主内容区。

### 页面清单（15 个核心页面）

| 模块 | 页面 |
|------|------|
| 通用 | 登录页、工作台（首页看板） |
| CRM | 客户列表、客户详情（含跟进时间线）、公海池 |
| 排期 | 排期日历（月/周/日视图）、活动详情、场地管理 |
| 订单 | 订单列表、订单详情、新建订单（含报价单预览） |
| 供应商 | 供应商列表、供应商详情 |
| 系统 | 员工管理、系统设置（角色权限/操作日志） |

### 工作台首页看板内容

- **统计卡片**：本月订单、营业额、待跟进客户、本月排期
- **待办事项**：收款提醒、跟进提醒、审批待办、执行提醒
- **近期排期**：按日期展示近期婚礼活动及状态

## 工程结构

### 后端（wedding-backend/）

```
wedding-backend/
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置管理
│   ├── database.py             # SQLAlchemy 引擎和 Session
│   ├── models/                 # ORM 模型
│   ├── schemas/                # Pydantic 请求/响应模型
│   ├── api/                    # 路由模块
│   ├── services/               # 业务逻辑层
│   ├── middleware/              # 中间件（认证/日志/CORS）
│   └── utils/                  # 工具函数
├── migrations/                 # Alembic 迁移
├── tests/                      # 测试
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### 前端（wedding-frontend/）

```
wedding-frontend/
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router/                 # 路由 + 权限守卫
│   ├── stores/                 # Pinia 状态管理
│   ├── api/                    # API 请求封装
│   ├── views/                  # 页面组件
│   ├── components/             # 通用组件
│   ├── layouts/                # 布局组件
│   └── utils/                  # 工具函数
├── package.json
├── vite.config.ts
├── Dockerfile
└── nginx.conf
```

### Docker Compose 部署

四个容器：frontend（Nginx）、backend（Uvicorn）、mysql（MySQL 8）、redis。

## 非功能性要求

- **认证**：JWT Token，Token 过期后自动刷新
- **日志**：所有关键操作写入 OperationLog
- **数据安全**：密码 bcrypt 加密存储，敏感字段脱敏
- **分页**：所有列表接口支持分页和排序
- **导出**：报价单支持 PDF 导出
