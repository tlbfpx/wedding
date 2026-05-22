# Customers 模块设计概览

## 模块职责

管理婚庆业务中客户的全生命周期，包括客户信息管理、跟进记录、客户公海池（回收/认领）、客户转移以及客户来源字典维护。

## 数据模型

### 实体关系图

```
CustomerSource (1) ──── (N) Customer (N) ──── (1) User (assigned_sale)
                                 │
                                 ├── (N) FollowUp ──── (1) User (sale)
```

### Customer（客户）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 主键 |
| name | string(50) | NOT NULL | 客户姓名 |
| phone | string(20) | UNIQUE, NOT NULL | 手机号（唯一标识） |
| gender | enum | 默认 `unknown` | 性别：`male` / `female` / `unknown` |
| source_id | int | FK → customer_sources.id, 可选 | 客户来源 |
| status | enum | 默认 `potential` | 客户状态 |
| budget_range | string(50) | 可选 | 预算范围（自由文本） |
| wedding_date | date | 可选 | 婚期 |
| note | text | 可选 | 备注 |
| assigned_sale_id | int | FK → users.id, 可选 | 指派销售 ID |
| recycled_at | datetime | 可选 | 回收到公海池的时间 |
| created_at | datetime | 自动 | 创建时间（继承自 TimestampMixin） |
| updated_at | datetime | 自动 | 更新时间（继承自 TimestampMixin） |

### CustomerStatus 枚举

| 值 | 说明 |
|---|------|
| `potential` | 潜在客户（新建默认状态） |
| `following` | 跟进中 |
| `intention` | 有意向 |
| `signed` | 已签约 |
| `lost` | 已流失 |

### FollowUp（跟进记录）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 主键 |
| customer_id | int | FK → customers.id, NOT NULL | 关联客户 |
| sale_id | int | FK → users.id, NOT NULL | 跟进销售 |
| type | enum | NOT NULL | 跟进方式 |
| content | text | NOT NULL | 跟进内容 |
| next_follow_at | datetime | 可选 | 下次跟进时间 |
| created_at | datetime | 默认当前时间 | 创建时间 |

### FollowUpType 枚举

| 值 | 说明 |
|---|------|
| `phone` | 电话跟进 |
| `wechat` | 微信跟进 |
| `visit` | 到店拜访 |
| `other` | 其他方式 |

### CustomerSource（客户来源字典）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 主键 |
| name | string(30) | UNIQUE, NOT NULL | 来源名称 |

## 业务规则

### 1. 手机号唯一性

- 客户手机号在系统中必须唯一
- 创建时校验，重复则返回 `DUPLICATE_PHONE` 错误
- 更新时不做重复校验（当前实现）

### 2. 乐观锁并发控制

- 更新客户时必须携带 `version` 字段
- `version` 基于记录的 `updated_at`（优先）或 `created_at` 时间戳生成
- 服务端比对 version，不一致则拒绝更新并返回 `VERSION_CONFLICT`
- 防止多人同时编辑同一客户信息

### 3. 客户公海池机制

- **回收**：销售将客户回收到公海池，`assigned_sale_id` 置空，记录 `recycled_at`
- **公海池**：所有 `assigned_sale_id` 为 `null` 的客户构成公海池
- **认领**：销售从公海池认领客户，`assigned_sale_id` 设为当前用户，清除 `recycled_at`，状态变为 `following`
- **唯一性**：认领时检查客户是否已被他人认领，防止并发抢客

### 4. 跟进自动流转

- 添加跟进记录时，若客户处于 `potential` 状态，自动升级为 `following`
- 跟进记录的 `sale_id` 自动设为当前操作用户

### 5. 客户转移

- 管理员或销售可将客户转移给其他销售
- 需验证目标销售存在且状态为 `active`

### 6. 操作日志

所有写操作（创建、更新、跟进、转移、回收、认领）均通过 `log_operation` 记录操作日志。

## 状态机

### 客户状态流转

```
                 ┌──────────────────────────────────────────────┐
                 │                                              │
                 ▼                                              │
[potential] ──添加跟进──▶ [following] ────▶ [intention] ────▶ [signed]
  新建默认             首次跟进自动流转        （手动变更）       （手动变更）
                 │                                              │
                 │                                              │
                 └──────────────────────────────────────────────┘
                                          │
                                          ▼
                                      [lost]
                                    （手动变更）
```

**状态流转规则**：

| 当前状态 | 可流转到 | 触发条件 |
|----------|---------|---------|
| `potential` | `following` | 添加第一条跟进记录时自动流转 |
| `following` | `intention` | 手动更新状态 |
| `following` | `lost` | 手动更新状态 |
| `following` | `signed` | 手动更新状态（通常由订单签约驱动） |
| `intention` | `signed` | 手动更新状态 |
| `intention` | `lost` | 手动更新状态 |
| `signed` | - | 终态（一般不再变更） |
| `lost` | - | 终态（一般不再变更） |

**注意**：当前实现中状态变更为直接赋值，未对流转路径做严格校验（除 `potential` → `following` 为自动触发外，其他状态变更均通过更新接口手动设置）。

### 公海池生命周期

```
[新建客户（未指派销售）] ──▶ [公海池]
                              │
                         销售认领
                              │
                              ▼
                    [已指派销售，status=following]
                              │
                         销售回收
                              │
                              ▼
                         [公海池]
```
