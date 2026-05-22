# Approvals 模块设计概览

## 模块职责

Approvals 模块负责婚庆管理系统中**业务审批流程的管理**，包括：

1. 审批单的创建（折扣审批、退款审批、取消订单审批）
2. 审批决策（通过/驳回）
3. 审批通过后自动执行关联业务动作

该模块与订单模块（Orders）和用户模块（Users）存在依赖关系。审批的目标对象为订单（`target_id` 关联 `Order.id`）。

## 数据模型

### Approval（审批）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 审批 ID |
| type | ApprovalType | NOT NULL | 审批类型 |
| target_id | int | NOT NULL | 目标 ID（关联订单 ID） |
| applicant_id | int | FK(users.id), NOT NULL | 申请人 ID |
| approver_id | int | FK(users.id), Nullable | 审批人 ID |
| status | ApprovalStatus | 默认 pending | 审批状态 |
| reason | text | NOT NULL | 申请原因 |
| note | text | Nullable | 审批备注 |
| resolved_at | datetime | Nullable | 处理时间 |
| created_at | datetime | 自动生成 | 创建时间 |

### 枚举类型

**ApprovalType（审批类型）**：

| 值 | 说明 |
|------|------|
| discount | 折扣审批 |
| refund | 退款审批 |
| cancel | 取消订单审批 |

**ApprovalStatus（审批状态）**：

| 值 | 说明 |
|------|------|
| pending | 待审批 |
| approved | 已通过 |
| rejected | 已驳回 |

## 业务规则

### 审批创建

1. 申请人 `applicant_id` 自动设为当前登录用户，不可手动指定
2. `target_id` 为审批目标对象的 ID，当前仅用于关联订单
3. `reason` 为必填字段，记录申请原因
4. 创建后审批状态默认为 `pending`

### 审批决策

1. **幂等性保护**：已处理的审批（状态非 `pending`）不可重复操作
2. **状态约束**：不允许将审批状态设为 `pending`（不可撤回已提交的审批）
3. **审批人记录**：审批人自动设为当前登录用户
4. **时间戳**：处理时自动记录 `resolved_at`

### 关联动作

审批通过后，根据审批类型自动执行关联业务动作：

| 审批类型 | 关联动作 | 说明 |
|----------|----------|------|
| cancel | 将订单状态设为 `cancelled` | 取消订单 |
| discount | 无额外动作 | 折扣在申请时已应用，审批仅做确认 |
| refund | 将订单 `paid_amount` 置为 0 | 标记全额退款 |

### 数据关联

1. **申请人/审批人**：通过 `applicant_id` 和 `approver_id` 关联用户，查询时批量加载用户姓名
2. **目标订单**：通过 `target_id` 关联订单，查询时批量加载订单编号 `order_no`
3. **批量加载优化**：使用 `IN` 查询批量加载关联数据，避免 N+1 查询问题

### 操作审计

所有写操作（POST/PUT/DELETE）通过 `log_operation` 中间件自动记录操作日志。

## 状态机

### 审批状态流转

```
pending ──→ approved
   │
   └──→ rejected
```

- `pending`（待审批）→ `approved`（已通过）：审批人批准
- `pending` → `rejected`（已驳回）：审批人驳回
- 状态流转为单向不可逆，已处理的审批不可撤回或重新提交
- 不存在 `approved` → `rejected` 或 `rejected` → `approved` 的流转

### 审批-订单联动

```
折扣申请创建 → [折扣已应用] → 审批通过（确认） → 订单折扣生效
退款申请创建 → 审批通过 → 订单 paid_amount 置 0
取消申请创建 → 审批通过 → 订单状态 → cancelled
```
