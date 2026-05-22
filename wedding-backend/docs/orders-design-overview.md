# Orders 模块设计概览

## 模块职责

管理婚庆业务中的订单全流程，包括订单创建（含报价明细）、状态流转、付款记录、合同管理和报价单 PDF 生成。

## 数据模型

### 实体关系图

```
Customer (1) ──── (N) Order (N) ──── (1) User (sale)
                       │                    │
                       ├── (N) OrderItem ───┤ (planner, 也关联 User)
                       │       │
                       │       └──── (1) Supplier (可选)
                       │
                       ├── (N) Payment
                       │
                       ├── (0..1) Contract
                       │
                       └── (N) Approval (审批)
```

### Order（订单）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 主键 |
| order_no | string(20) | UNIQUE, NOT NULL | 订单号，格式 `WD{YYYYMMDD}{NNN}` |
| customer_id | int | FK → customers.id, NOT NULL | 关联客户 |
| planner_id | int | FK → users.id, 可选 | 策划师 |
| sale_id | int | FK → users.id, NOT NULL | 销售 |
| status | enum | 默认 `intention` | 订单状态 |
| total_amount | decimal(12,2) | 默认 0 | 订单总额（折扣后） |
| paid_amount | decimal(12,2) | 默认 0 | 已付金额 |
| discount | decimal(3,2) | 默认 1.00 | 折扣系数（1.00 = 无折扣） |
| note | text | 可选 | 备注 |
| created_at | datetime | 自动 | 创建时间（继承自 TimestampMixin） |
| updated_at | datetime | 自动 | 更新时间（继承自 TimestampMixin） |

### OrderStatus 枚举

| 值 | 说明 |
|---|------|
| `intention` | 意向（初始状态） |
| `signed` | 已签约 |
| `executing` | 执行中 |
| `completed` | 已完成 |
| `cancelled` | 已取消 |

### OrderItem（订单项）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 主键 |
| order_id | int | FK → orders.id, NOT NULL | 关联订单 |
| type | enum | NOT NULL | 项目类型 |
| name | string(100) | NOT NULL | 项目名称 |
| quantity | int | 默认 1 | 数量 |
| unit_price | decimal(10,2) | NOT NULL | 单价 |
| amount | decimal(10,2) | NOT NULL | 小计金额（= unit_price x quantity） |
| supplier_id | int | FK → suppliers.id, 可选 | 关联供应商 |
| note | string(200) | 可选 | 备注 |

### ItemType 枚举

| 值 | 说明 |
|---|------|
| `planning` | 策划 |
| `venue` | 场地 |
| `floral` | 花艺 |
| `photo` | 摄影 |
| `host` | 主持 |
| `car` | 婚车 |
| `other` | 其他 |

### Payment（付款记录）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 主键 |
| order_id | int | FK → orders.id, NOT NULL | 关联订单 |
| amount | decimal(12,2) | NOT NULL | 付款金额 |
| method | enum | NOT NULL | 付款方式 |
| status | enum | 默认 `pending` | 付款状态 |
| paid_at | datetime | 可选 | 实际付款时间 |
| note | string(200) | 可选 | 备注 |
| created_at | datetime | 默认当前时间 | 创建时间 |

### PaymentMethod 枚举

| 值 | 说明 |
|---|------|
| `cash` | 现金 |
| `transfer` | 银行转账 |
| `wechat` | 微信支付 |
| `alipay` | 支付宝 |
| `card` | 刷卡 |

### PaymentStatus 枚举

| 值 | 说明 |
|---|------|
| `pending` | 待确认 |
| `confirmed` | 已确认 |

### Contract（合同）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 主键 |
| order_id | int | FK → orders.id, NOT NULL | 关联订单 |
| file_url | string(500) | NOT NULL | 合同文件路径 |
| status | enum | 默认 `pending` | 合同状态 |
| signed_at | datetime | 可选 | 签署时间 |

### ContractStatus 枚举

| 值 | 说明 |
|---|------|
| `pending` | 待签署 |
| `signed` | 已签署 |

### Approval（审批）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 主键 |
| type | enum | NOT NULL | 审批类型 |
| target_id | int | NOT NULL | 审批目标 ID |
| applicant_id | int | FK → users.id, NOT NULL | 申请人 |
| approver_id | int | FK → users.id, 可选 | 审批人 |
| status | enum | 默认 `pending` | 审批状态 |
| reason | text | NOT NULL | 申请理由 |
| note | text | 可选 | 审批备注 |
| resolved_at | datetime | 可选 | 审批时间 |
| created_at | datetime | 默认当前时间 | 创建时间 |

### ApprovalType 枚举

| 值 | 说明 |
|---|------|
| `discount` | 折扣审批 |
| `refund` | 退款审批 |
| `cancel` | 取消审批 |

### ApprovalStatus 枚举

| 值 | 说明 |
|---|------|
| `pending` | 待审批 |
| `approved` | 已通过 |
| `rejected` | 已拒绝 |

## 业务规则

### 1. 订单号生成规则

- 格式：`WD{YYYYMMDD}{NNN}`
- 前缀 `WD` + 当天日期（YYYYMMDD）+ 当日序号（3位补零）
- 序号基于当天已有订单数量 +1
- 注意：当前实现在高并发场景下可能生成重复订单号（未使用数据库锁或唯一约束重试）

### 2. 订单金额计算

- 每个订单项 `amount = unit_price x quantity`
- 订单总额 `total_amount = SUM(所有订单项 amount) x discount`
- 折扣系数 `discount` 默认 1.00（无折扣）
- 注意：更新订单的 discount 时不会自动重算 total_amount

### 3. 付款控制

- 付款后已付总额不能超过订单总额（`paid_amount + new_amount <= total_amount`）
- 每次付款自动将 Payment 状态设为 `confirmed`，记录 `paid_at`
- 同时更新订单的 `paid_amount`

### 4. 订单编辑限制

- 仅 `intention`（意向）状态的订单允许修改基本信息（note、discount、planner_id）
- 其他状态下的订单只能通过状态流转接口变更状态

### 5. 合同管理

- 每个订单最多一条合同记录
- 上传新合同会覆盖旧合同（更新 file_url，状态重置为 pending）
- 合同文件存储在本地文件系统，路径通过 `settings.UPLOAD_DIR` 配置

### 6. 报价单 PDF 生成

- 使用 reportlab 库动态生成 PDF
- 包含订单基本信息、项目明细、金额汇总
- 以流式响应返回，不持久化到文件系统

### 7. 操作日志

所有写操作（创建、更新、状态变更、付款、上传合同）均通过 `log_operation` 记录操作日志。

## 状态机

### 订单状态流转

```
[intention] ──签约──▶ [signed] ──开始执行──▶ [executing] ──完成──▶ [completed]
    │                    │                      │
    │                    │                      │
    ▼                    ▼                      ▼
[cancelled]          [cancelled]            [cancelled]
```

**合法转换矩阵**：

| 当前状态 | 可流转到 | 说明 |
|----------|---------|------|
| `intention` | `signed` | 签约 |
| `intention` | `cancelled` | 取消 |
| `signed` | `executing` | 开始执行 |
| `signed` | `cancelled` | 取消 |
| `executing` | `completed` | 完成 |
| `executing` | `cancelled` | 取消 |
| `completed` | - | 终态，不可变更 |
| `cancelled` | - | 终态，不可变更 |

**校验方式**：通过 `VALID_TRANSITIONS` 字典严格校验，非法转换返回 `INVALID_TRANSITION` 错误。
