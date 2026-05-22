# Suppliers 模块设计概览

## 模块职责

管理婚庆业务中的供应商资源，包括供应商信息维护、服务项目管理、供应商评价及评分管理。

## 数据模型

### 实体关系图

```
Supplier (1) ──── (N) SupplierService
     │
     └──── (N) SupplierEvaluation ──── (1) Order
                              │
                              └──── (1) User (evaluator)
```

### Supplier（供应商）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 主键 |
| name | string(100) | NOT NULL | 供应商名称 |
| type | enum | NOT NULL | 供应商类型 |
| contact | string(50) | 可选 | 联系人 |
| phone | string(20) | 可选 | 联系电话 |
| address | string(200) | 可选 | 地址 |
| cooperation_status | enum | 默认 `active` | 合作状态 |
| rating | decimal(2,1) | 默认 0.0 | 平均评分（1.0-5.0） |
| note | text | 可选 | 备注 |
| created_at | datetime | 自动 | 创建时间（继承自 TimestampMixin） |
| updated_at | datetime | 自动 | 更新时间（继承自 TimestampMixin） |

### SupplierType 枚举

| 值 | 说明 | 对应订单项类型 |
|---|------|---------------|
| `four_gods` | 四大金刚（摄影+摄像+化妆+主持） | 无直接对应 |
| `car` | 婚车 | `car` |
| `venue` | 场地 | `venue` |
| `floral` | 花艺 | `floral` |
| `photo` | 摄影/摄像 | `photo` |
| `host` | 主持 | `host` |
| `other` | 其他 | `other` |

### CooperationStatus 枚举

| 值 | 说明 |
|---|------|
| `active` | 合作中 |
| `suspended` | 暂停合作 |
| `blacklist` | 黑名单 |

### SupplierService（供应商服务项）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 主键 |
| supplier_id | int | FK → suppliers.id, NOT NULL | 关联供应商 |
| service_name | string(100) | NOT NULL | 服务名称 |
| description | text | 可选 | 服务描述 |
| price | decimal(10,2) | NOT NULL | 服务价格 |
| unit | string(20) | 默认 `"次"` | 计价单位 |
| note | string(200) | 可选 | 备注 |

### SupplierEvaluation（供应商评价）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 主键 |
| supplier_id | int | FK → suppliers.id, NOT NULL | 关联供应商 |
| order_id | int | FK → orders.id, NOT NULL | 关联订单 |
| rating | int | NOT NULL | 评分（1-5） |
| content | text | 可选 | 评价内容 |
| evaluator_id | int | FK → users.id, NOT NULL | 评价人 |
| created_at | datetime | 默认当前时间 | 创建时间 |

## 业务规则

### 1. 供应商评分机制

- 新建供应商评分为 0.0
- 每次添加评价后自动重算平均评分
- 计算公式：`新平均分 = (当前平均分 x 当前评价数 + 新评分) / (当前评价数 + 1)`
  - 注意：当前实现存在精度问题——在添加评价记录后查询的 `count` 已包含新记录，但实际上新记录尚未 flush 到数据库，可能导致计算偏差。实际行为取决于 SQLAlchemy 的 session flush 时机。
- 评分保留一位小数（`round(new_avg, 1)`）

### 2. 合作状态管理

- 供应商有三种合作状态：合作中、暂停合作、黑名单
- 状态变更通过更新供应商接口直接设置
- 当前未实现状态变更的业务约束（如暂停合作的供应商是否可被新订单引用等）

### 3. 服务项目管理

- 每个供应商可有多个服务项目
- 服务项目独立 CRUD，通过 `supplier_id` 关联供应商
- 服务价格使用 decimal(10,2) 存储，精确到分
- 更新服务时同时验证 `supplier_id` 和 `service_id`，防止越权操作

### 4. 评价与订单关联

- 评价必须关联一个订单（`order_id`）
- 评价必须关联一个评价人（`evaluator_id`，自动设为当前用户）
- 评分范围：1-5（整数），超出范围返回 `INVALID_RATING`
- 当前未限制同一订单对同一供应商的重复评价

### 5. 操作日志

所有写操作（创建、更新供应商、添加/更新服务、添加评价）均通过 `log_operation` 记录操作日志。

## 状态机

### 合作状态流转

```
[active] ──暂停──▶ [suspended] ──恢复──▶ [active]
    │                   │
    │                   │
    ▼                   ▼
[blacklist]          [blacklist]
```

**状态说明**：

| 状态 | 说明 | 业务含义 |
|------|------|---------|
| `active` | 合作中 | 正常合作，可被订单引用 |
| `suspended` | 暂停合作 | 临时停止合作，当前未强制限制新订单引用 |
| `blacklist` | 黑名单 | 不再合作，当前未强制限制新订单引用 |

**注意**：当前实现中合作状态为直接赋值，无严格的流转校验。任意状态之间可以互相切换。
