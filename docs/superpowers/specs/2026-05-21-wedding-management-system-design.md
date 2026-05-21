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

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| name | VARCHAR(50) | NOT NULL | 客户姓名 |
| phone | VARCHAR(20) | NOT NULL, UNIQUE | 手机号，格式校验 11 位 |
| gender | ENUM('male','female','unknown') | DEFAULT 'unknown' | |
| source_id | INT | FK → CustomerSource.id | 客户来源 |
| status | ENUM('potential','following','intention','signed','lost') | DEFAULT 'potential' | 潜在/跟进中/有意向/已签约/已流失 |
| budget_range | VARCHAR(50) | NULL | 预算范围（如 "5-10万"），自由填写 |
| wedding_date | DATE | NULL | 预计婚期 |
| note | TEXT | NULL | 备注 |
| assigned_sale_id | INT | FK → User.id, NULL | 分配的销售，NULL 表示在公海池 |
| recycled_at | DATETIME | NULL | 回收到公海池的时间 |
| created_at | DATETIME | DEFAULT NOW() | |
| updated_at | DATETIME | ON UPDATE NOW() | |

索引：(assigned_sale_id), (status), (phone), (created_at)

**FollowUp（跟进记录）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| customer_id | INT | FK → Customer.id, NOT NULL | |
| sale_id | INT | FK → User.id, NOT NULL | |
| type | ENUM('phone','wechat','visit','other') | NOT NULL | 电话/微信/面访/其他 |
| content | TEXT | NOT NULL | 跟进内容 |
| next_follow_at | DATETIME | NULL | 下次跟进时间 |
| created_at | DATETIME | DEFAULT NOW() | |

索引：(customer_id), (sale_id), (next_follow_at)

**CustomerSource（客户来源）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| name | VARCHAR(30) | NOT NULL, UNIQUE | 线上咨询/转介绍/线下门店/小红书/抖音/其他 |

### 排期与资源管理模块

**Event（活动/婚礼）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| order_id | INT | FK → Order.id, UNIQUE | 一个订单对应一场活动（1:1） |
| title | VARCHAR(100) | NOT NULL | 活动标题（如"张先生 & 李女士婚礼"） |
| date | DATE | NOT NULL | 活动日期 |
| start_time | TIME | NULL | 开始时间 |
| end_time | TIME | NULL | 结束时间 |
| venue_id | INT | FK → Venue.id, NULL | 场地 |
| status | ENUM('draft','confirmed','executing','completed','cancelled') | DEFAULT 'draft' | 草稿/已确认/执行中/已完成/已取消 |
| planner_id | INT | FK → User.id, NULL | 负责策划师 |
| note | TEXT | NULL | |

索引：(date), (venue_id), (planner_id), (status)

**EventResource（活动资源分配）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| event_id | INT | FK → Event.id, NOT NULL | |
| resource_type | ENUM('staff','venue','vehicle','equipment','other') | NOT NULL | 资源类型 |
| resource_id | INT | NOT NULL | 对应资源的 ID（多态关联） |
| quantity | INT | DEFAULT 1 | 数量 |
| note | VARCHAR(200) | NULL | |

索引：(event_id), (resource_type, resource_id)

**StaffSchedule（人员排班）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| staff_id | INT | FK → User.id, NOT NULL | |
| event_id | INT | FK → Event.id, NOT NULL | |
| role | VARCHAR(30) | NOT NULL | 当天角色（策划师/花艺师/摄影师等） |
| date | DATE | NOT NULL | |
| status | ENUM('assigned','confirmed','completed') | DEFAULT 'assigned' | |

索引：(staff_id, date), (event_id)

**Venue（场地）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| name | VARCHAR(100) | NOT NULL, UNIQUE | 场地名称 |
| address | VARCHAR(200) | NULL | 地址 |
| capacity | INT | NULL | 容纳人数 |
| contact | VARCHAR(50) | NULL | 联系人 |
| phone | VARCHAR(20) | NULL | 联系电话 |
| price | DECIMAL(10,2) | NULL | 参考价格 |
| note | TEXT | NULL | |

### 订单与财务模块

**Order（订单）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| order_no | VARCHAR(20) | NOT NULL, UNIQUE | 自动生成，格式 WD20260521001 |
| customer_id | INT | FK → Customer.id, NOT NULL | |
| planner_id | INT | FK → User.id, NULL | 策划师 |
| sale_id | INT | FK → User.id, NOT NULL | 销售 |
| status | ENUM('intention','signed','executing','completed','cancelled') | DEFAULT 'intention' | 意向/已签约/执行中/已完成/已取消 |
| total_amount | DECIMAL(12,2) | NOT NULL, DEFAULT 0 | 总金额 |
| paid_amount | DECIMAL(12,2) | NOT NULL, DEFAULT 0 | 已收金额 |
| discount | DECIMAL(3,2) | DEFAULT 1.00 | 折扣（如 0.90 表示九折），需审批 |
| note | TEXT | NULL | |
| created_at | DATETIME | DEFAULT NOW() | |
| updated_at | DATETIME | ON UPDATE NOW() | |

索引：(customer_id), (sale_id), (status), (created_at)

**订单状态流转规则**：意向 → 已签约 → 执行中 → 已完成；任意状态可 → 已取消（需审批）。不可逆向流转。

**OrderItem（订单明细）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| order_id | INT | FK → Order.id, NOT NULL | |
| type | ENUM('planning','venue','floral','photo','host','car','other') | NOT NULL | 策划/场地/花艺/摄影/主持/婚车/其他 |
| name | VARCHAR(100) | NOT NULL | 服务名称 |
| quantity | INT | NOT NULL, DEFAULT 1 | |
| unit_price | DECIMAL(10,2) | NOT NULL | 单价 |
| amount | DECIMAL(10,2) | NOT NULL | 小计 = quantity × unit_price |
| supplier_id | INT | FK → Supplier.id, NULL | 关联供应商 |
| note | VARCHAR(200) | NULL | |

索引：(order_id), (supplier_id)

**Payment（收款记录）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| order_id | INT | FK → Order.id, NOT NULL | |
| amount | DECIMAL(12,2) | NOT NULL, CHECK > 0 | 收款金额 |
| method | ENUM('cash','transfer','wechat','alipay','card') | NOT NULL | 现金/转账/微信/支付宝/刷卡 |
| status | ENUM('pending','confirmed') | DEFAULT 'pending' | 待确认/已确认 |
| paid_at | DATETIME | NULL | 实际支付时间 |
| note | VARCHAR(200) | NULL | |

索引：(order_id), (status)

**Contract（合同）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| order_id | INT | FK → Order.id, NOT NULL | |
| file_url | VARCHAR(500) | NOT NULL | 文件存储路径 |
| status | ENUM('pending','signed') | DEFAULT 'pending' | |
| signed_at | DATETIME | NULL | 签署日期 |

索引：(order_id)

**Approval（审批）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| type | ENUM('discount','refund','cancel') | NOT NULL | 折扣审批/退款审批/取消审批 |
| target_id | INT | NOT NULL | 关联的实体 ID（Order.id 或 Payment.id） |
| applicant_id | INT | FK → User.id, NOT NULL | 申请人 |
| approver_id | INT | FK → User.id, NULL | 审批人（管理员角色） |
| status | ENUM('pending','approved','rejected') | DEFAULT 'pending' | |
| reason | TEXT | NOT NULL | 申请/审批理由 |
| resolved_at | DATETIME | NULL | 审批时间 |
| created_at | DATETIME | DEFAULT NOW() | |

索引：(status), (applicant_id), (approver_id)

**审批流程**：申请人发起 → 管理员收到通知 → 通过/驳回。审批通过后自动执行（折扣生效/退款确认/订单取消）。当前为单级审批。

### 供应商管理模块

**Supplier（供应商）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| name | VARCHAR(100) | NOT NULL | 供应商名称 |
| type | ENUM('four_gods','car','venue','floral','photo','host','other') | NOT NULL | 四大金刚/婚车/场地/花艺/摄影摄像/主持/其他 |
| contact | VARCHAR(50) | NULL | 联系人 |
| phone | VARCHAR(20) | NULL | 联系电话 |
| address | VARCHAR(200) | NULL | 地址 |
| cooperation_status | ENUM('active','suspended','blacklist') | DEFAULT 'active' | 合作中/暂停/黑名单 |
| rating | DECIMAL(2,1) | DEFAULT 0.0 | 综合评分 0.0-5.0，由评价自动计算 |
| note | TEXT | NULL | |

索引：(type), (cooperation_status), (rating)

**SupplierService（供应商服务/报价）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| supplier_id | INT | FK → Supplier.id, NOT NULL | |
| service_name | VARCHAR(100) | NOT NULL | 服务名称 |
| description | TEXT | NULL | 服务描述 |
| price | DECIMAL(10,2) | NOT NULL | 价格 |
| unit | VARCHAR(20) | DEFAULT '次' | 计量单位（次/天/套等） |
| note | VARCHAR(200) | NULL | |

索引：(supplier_id)

**SupplierEvaluation（供应商评价）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| supplier_id | INT | FK → Supplier.id, NOT NULL | |
| order_id | INT | FK → Order.id, NOT NULL | |
| rating | TINYINT | NOT NULL, CHECK 1-5 | 评分 |
| content | TEXT | NULL | 评价内容 |
| evaluator_id | INT | FK → User.id, NOT NULL | 评价人 |
| created_at | DATETIME | DEFAULT NOW() | |

索引：(supplier_id), (order_id)

### 公共实体

**User（用户/员工）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| username | VARCHAR(50) | NOT NULL, UNIQUE | 登录名 |
| password_hash | VARCHAR(200) | NOT NULL | bcrypt 加密 |
| name | VARCHAR(50) | NOT NULL | 真实姓名 |
| phone | VARCHAR(20) | NULL | 手机号 |
| role_id | INT | FK → Role.id, NOT NULL | 角色 |
| team | ENUM('sales','planning','design','management') | NOT NULL | 所属团队 |
| status | ENUM('active','inactive') | DEFAULT 'active' | 在职/离职 |

索引：(username), (team), (status)

**Role（角色）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| name | VARCHAR(50) | NOT NULL, UNIQUE | 角色名称 |
| permissions | JSON | NOT NULL | 权限配置 |

权限 JSON 结构：
```json
{
  "crm": { "read": "all|team|own|none", "write": "all|team|own|none" },
  "schedule": { "read": "all|team|own|none", "write": "all|team|own|none" },
  "order": { "read": "all|team|own|none", "write": "all|team|own|none" },
  "supplier": { "read": "all|team|own|none", "write": "all|team|own|none" },
  "dashboard": "all|team|none",
  "system": true|false
}
```

**OperationLog（操作日志）**

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INT | PK, AUTO_INCREMENT | |
| user_id | INT | FK → User.id, NOT NULL | 操作人 |
| module | VARCHAR(30) | NOT NULL | 模块名（customer/order/event/supplier/system） |
| action | VARCHAR(30) | NOT NULL | 操作（create/update/delete/transfer/recycle/approve） |
| target | VARCHAR(100) | NULL | 操作对象标识 |
| detail | TEXT | NULL | 操作详情（JSON 格式，记录变更前后值） |
| ip | VARCHAR(45) | NULL | 客户端 IP |
| created_at | DATETIME | DEFAULT NOW() | |

索引：(user_id), (module), (created_at)

日志通过中间件自动记录，无需手动调用。记录所有 POST/PUT/DELETE 请求的变更。

### 核心关系

- Customer → Order（1:N）
- Order → OrderItem（1:N）
- Order → Event（1:1，Event.order_id UNIQUE 约束保证）
- OrderItem → Supplier（N:1）
- Event → StaffSchedule（1:N）
- Event → EventResource（1:N）
- Customer → FollowUp（1:N）
- Supplier → SupplierEvaluation（1:N）

## API 通用规范

### 分页

所有列表接口统一使用 cursor-free 分页：

**请求参数**：
- `page`：页码，从 1 开始，默认 1
- `page_size`：每页条数，默认 20，最大 100
- `sort_by`：排序字段，默认 `created_at`
- `sort_order`：排序方向，`asc` 或 `desc`，默认 `desc`

**响应格式**：
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

### 错误处理

**统一错误响应格式**：
```json
{
  "error": {
    "code": "CUSTOMER_NOT_FOUND",
    "message": "客户不存在",
    "details": null
  }
}
```

**HTTP 状态码规范**：
- 200：成功
- 201：创建成功
- 400：请求参数错误
- 401：未认证
- 403：无权限
- 404：资源不存在
- 409：业务冲突（如手机号重复、排期冲突）
- 422：数据校验失败（Pydantic 自动处理）
- 500：服务器内部错误

**常见业务错误码**：
| code | 说明 |
|------|------|
| DUPLICATE_PHONE | 手机号已存在 |
| CUSTOMER_NOT_FOUND | 客户不存在 |
| ORDER_STATUS_INVALID | 订单状态流转不合法 |
| INSUFFICIENT_PERMISSION | 权限不足 |
| SCHEDULE_CONFLICT | 排期冲突（同人员/同场地） |
| APPROVAL_REQUIRED | 需要审批（如折扣低于 9 折） |
| INVALID_DISCOUNT | 折扣值不合法 |

### 认证

JWT 认证，Access Token 有效期 2 小时，Refresh Token 有效期 7 天。

- Access Token 存储在 LocalStorage，每次请求通过 `Authorization: Bearer <token>` 传递
- Refresh Token 存储在 HttpOnly Cookie
- `/api/auth/logout` 将 Token 加入 Redis 黑名单，实现即时失效
- Token 刷新：Access Token 过期后前端自动用 Refresh Token 换取新 Token

### 文件上传

- 合同上传：仅允许 PDF/JPG/PNG，最大 10MB
- 存储：本地文件系统 `uploads/` 目录，部署时挂载为 Docker Volume
- 命名：`{entity_type}/{entity_id}/{timestamp}_{original_filename}`
- `file_url` 返回相对路径，前端拼接域名

### 公海池规则

- 客户超过 **15 天**无跟进记录，系统自动回收到公海池（每日定时任务检查）
- 销售手动回收也可将客户放入公海池
- 公海池中的客户任何销售都可以认领
- 认领后 `assigned_sale_id` 更新，`recycled_at` 清空
- 回收不删除跟进记录，保留完整历史

### 冲突检测规则

- **场地冲突**：同一 venue_id + 同一 date，不允许重叠
- **人员冲突**：同一 staff_id + 同一 date，同一天只允许分配一个 Event
- 冲突检测为**阻断性**（blocking），返回 409 和冲突详情
- 编辑活动时排除自身进行检测

### 数据删除策略

采用软删除/状态变更，不硬删除业务数据：
- 客户：不可删除，只能标记为"已流失"
- 订单：已签约后不可删除，只能"取消"（需审批）
- 供应商：不可删除，改为"暂停"或"黑名单"状态
- 员工：不可删除，改为"离职"状态

### API 版本

所有 API 前缀为 `/api/v1/`，便于后续版本迭代。

## API 设计

### 认证

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | /api/v1/auth/login | 登录，返回 JWT |
| POST | /api/v1/auth/logout | 登出（Token 加入黑名单） |
| GET | /api/v1/auth/me | 获取当前用户信息 |
| POST | /api/v1/auth/refresh | 刷新 Token |

### CRM 客户管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /api/v1/customers | 客户列表。筛选：`source_id`, `status`, `assigned_sale_id`, `keyword`（姓名/手机模糊搜索）, `date_start`, `date_end` |
| GET | /api/v1/customers/{id} | 客户详情（含最近跟进记录） |
| POST | /api/v1/customers | 新增客户（phone 唯一性校验） |
| PUT | /api/v1/customers/{id} | 编辑客户 |
| POST | /api/v1/customers/{id}/follow-ups | 新增跟进记录 |
| POST | /api/v1/customers/{id}/transfer | 转移客户。参数：`target_sale_id` |
| POST | /api/v1/customers/{id}/recycle | 回收到公海池 |
| GET | /api/v1/customer-pool | 公海池列表。筛选：`source_id`, `keyword`, `recycled_days`（回收天数） |
| POST | /api/v1/customer-pool/{id}/claim | 从公海池认领客户 |

### 排期与资源管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /api/v1/events | 活动列表。筛选：`month`（YYYY-MM）, `date_start`, `date_end`, `status`, `planner_id`, `venue_id` |
| GET | /api/v1/events/{id} | 活动详情（含资源分配和人员排班） |
| POST | /api/v1/events | 新建活动（自动触发冲突检测） |
| PUT | /api/v1/events/{id} | 编辑活动（自动触发冲突检测） |
| GET | /api/v1/events/{id}/resources | 活动资源列表 |
| POST | /api/v1/events/{id}/resources | 分配资源 |
| DELETE | /api/v1/events/{id}/resources/{rid} | 移除资源 |
| GET | /api/v1/staff-schedule | 人员排班查询。筛选：`date`, `staff_id`, `event_id` |
| GET | /api/v1/venues | 场地列表。筛选：`keyword`, `capacity_min` |
| POST | /api/v1/venues | 新增场地 |
| PUT | /api/v1/venues/{id} | 编辑场地 |
| GET | /api/v1/venues/{id}/availability | 场地档期。参数：`date_start`, `date_end` |
| GET | /api/v1/conflicts | 冲突检测。参数：`venue_id`, `date`, `staff_ids`（逗号分隔）, `exclude_event_id` |

### 订单与财务

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /api/v1/orders | 订单列表。筛选：`status`, `sale_id`, `planner_id`, `keyword`（订单号/客户名）, `date_start`, `date_end` |
| GET | /api/v1/orders/{id} | 订单详情（含明细 + 收款记录 + 合同） |
| POST | /api/v1/orders | 新建订单（校验 discount，< 0.9 自动发起审批） |
| PUT | /api/v1/orders/{id} | 编辑订单（仅意向状态可编辑） |
| PUT | /api/v1/orders/{id}/status | 更新订单状态（校验状态流转规则） |
| POST | /api/v1/orders/{id}/payments | 登记收款（更新 Order.paid_amount） |
| POST | /api/v1/orders/{id}/contract | 上传合同文件。multipart/form-data |
| GET | /api/v1/orders/{id}/quote-pdf | 导出报价单 PDF |
| GET | /api/v1/approvals | 审批列表。筛选：`status`, `type`, `applicant_id` |
| POST | /api/v1/approvals | 发起审批（折扣/退款/取消） |
| PUT | /api/v1/approvals/{id} | 审批操作。参数：`action`（approve/reject）, `reason` |

### 供应商管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /api/v1/suppliers | 供应商列表。筛选：`type`, `cooperation_status`, `keyword`（名称/联系人）, `rating_min` |
| GET | /api/v1/suppliers/{id} | 供应商详情（含服务项目 + 最近评价） |
| POST | /api/v1/suppliers | 新增供应商 |
| PUT | /api/v1/suppliers/{id} | 编辑供应商 |
| GET | /api/v1/suppliers/{id}/services | 供应商服务报价列表 |
| POST | /api/v1/suppliers/{id}/services | 新增服务报价 |
| PUT | /api/v1/suppliers/{id}/services/{sid} | 编辑服务报价 |
| POST | /api/v1/suppliers/{id}/evaluations | 新增供应商评价（自动更新 Supplier.rating 均值） |
| GET | /api/v1/suppliers/{id}/evaluations | 供应商评价列表 |

### 数据看板

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /api/v1/dashboard/overview | 总览。参数：`period`（month/quarter/year），数据缓存 5 分钟 |
| GET | /api/v1/dashboard/sales-ranking | 销售排行。参数：`period`, `team` |
| GET | /api/v1/dashboard/conversion-funnel | 转化漏斗。参数：`date_start`, `date_end` |
| GET | /api/v1/dashboard/finance-summary | 收款统计。参数：`period` |
| GET | /api/v1/dashboard/schedule-heatmap | 排期热力图。参数：`month` |
| GET | /api/v1/dashboard/supplier-ranking | 供应商满意度。参数：`type` |

### 系统管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | /api/v1/users | 员工列表。筛选：`team`, `status`, `keyword` |
| POST | /api/v1/users | 新增员工 |
| PUT | /api/v1/users/{id} | 编辑员工（含重置密码） |
| GET | /api/v1/roles | 角色列表 |
| PUT | /api/v1/roles/{id} | 编辑角色权限（permissions JSON） |
| GET | /api/v1/operation-logs | 操作日志。筛选：`user_id`, `module`, `action`, `date_start`, `date_end` |

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

### 认证与安全

- 密码 bcrypt 加密存储，salt rounds = 12
- 登录失败 5 次后锁定账户 30 分钟（Redis 计数）
- 敏感字段脱敏：API 响应中手机号显示为 138****1234
- CORS 仅允许前端域名

### Redis 使用规范

| 用途 | Key 格式 | TTL |
|------|----------|-----|
| JWT 黑名单 | `jwt:blacklist:{token}` | 与 Token 过期时间一致 |
| 登录失败计数 | `login:fail:{username}` | 30 分钟 |
| 排期锁 | `lock:event:{venue_id}:{date}` | 10 秒（创建/编辑活动时 Redis 分布式锁） |
| 看板缓存 | `cache:dashboard:{endpoint}:{params}` | 5 分钟 |

### 并发控制

- 订单/客户编辑使用 `updated_at` 乐观锁：请求时携带 `updated_at`，后端比对不一致则返回 409
- 活动创建/编辑使用 Redis 分布式锁防止同一场地同时被分配

### 数据备份

Docker Compose 中 MySQL 容器挂载 volume，生产环境建议每日 mysqldump 备份到外部存储。

### 依赖说明

后端 Python 异步 MySQL 驱动使用 `asyncmy`（SQLAlchemy 2.0 async + MySQL）。
