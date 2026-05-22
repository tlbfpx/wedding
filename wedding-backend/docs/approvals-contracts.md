# Approvals 模块接口契约

## Service 接口

Approvals 模块当前未定义独立的 Service 层。辅助函数 `_execute_approval_action` 提供审批通过后的关联动作执行。

| 函数 | 说明 |
|------|------|
| `_execute_approval_action(db, approval)` | 审批通过后执行关联动作（取消订单、确认折扣、退款） |

## Controller 接口（HTTP API）

基础路径：`/api/v1/approvals`

### 1. 获取审批列表

- **方法**：`GET /api/v1/approvals`
- **认证**：Bearer Token（必需）
- **查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | ApprovalStatus | 否 | 状态筛选（pending/approved/rejected） |
| type | ApprovalType | 否 | 类型筛选（discount/refund/cancel） |
| applicant_id | int | 否 | 申请人 ID 筛选 |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 20，最大 100 |

- **响应**：`PageResponse<Approval>`
```json
{
  "items": [
    {
      "id": 1,
      "type": "discount",
      "target_id": 5,
      "order_id": 5,
      "order_no": "ORD20260520001",
      "applicant_id": 2,
      "applicant": {"id": 2, "name": "张销售"},
      "approver_id": 1,
      "approver": {"id": 1, "name": "管理员"},
      "status": "approved",
      "reason": "大客户优惠",
      "approver_remark": "同意",
      "resolved_at": "2026-05-21T14:30:00",
      "created_at": "2026-05-21T10:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

### 2. 创建审批

- **方法**：`POST /api/v1/approvals`
- **认证**：Bearer Token（必需）
- **请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | ApprovalType | 是 | 审批类型（discount/refund/cancel） |
| target_id | int | 是 | 目标 ID（通常为订单 ID） |
| reason | string | 是 | 申请原因 |

- **业务规则**：
  - 申请人自动设为当前登录用户
  - 审批状态默认为 `pending`
- **响应**：单个审批对象
- **注意**：响应中 `order_id` 和 `order_no` 在创建时可能为 `null`（未加载订单信息）

### 3. 审批决策（通过/驳回）

- **方法**：`PUT /api/v1/approvals/{approval_id}`
- **认证**：Bearer Token（必需）
- **路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| approval_id | int | 审批 ID |

- **请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | ApprovalStatus | 是 | 决策结果（approved/rejected） |
| note | string | 否 | 审批备注 |

- **业务规则**：
  - 不允许将状态设为 `pending`，返回 `400 INVALID_STATUS`
  - 已处理（非 pending）的审批不可再次操作，返回 `400 ALREADY_RESOLVED`
  - 审批人自动设为当前登录用户
  - 记录处理时间 `resolved_at`
  - 若决策为 `approved`，自动执行关联动作：
    - **cancel（取消订单）**：将关联订单状态设为 `cancelled`
    - **discount（折扣确认）**：折扣已在申请时应用，审批仅做确认，无额外动作
    - **refund（退款）**：将关联订单的 `paid_amount` 置为 0
- **响应**：单个审批对象
- **错误**：`404 NOT_FOUND` - 审批不存在；`400 ALREADY_RESOLVED` - 审批已处理；`400 INVALID_STATUS` - 无效状态

## Events（领域事件）

当前模块未显式定义领域事件。模块通过操作日志（`OperationLog`）记录写操作审计信息。
