# Orders 模块接口契约

## Service 接口（暴露给其他模块）

本模块目前未封装独立的 Service 层，其他模块通过数据库模型和 ID 引用关联：

- **Order 实体**：通过 `customer_id` 关联 Customers 模块；通过 `sale_id` / `planner_id` 关联 Users 模块。
- **OrderItem 实体**：通过 `supplier_id` 外键关联 Suppliers 模块，用于关联订单项与供应商。
- **SupplierEvaluation 实体**（Suppliers 模块定义）：通过 `order_id` 外键引用 `orders.id`，用于记录订单维度的供应商评价。

## Controller 接口（HTTP API）

基础路径：`/api/v1/orders`

### 1. 订单列表查询

- **方法**：`GET /api/v1/orders`
- **认证**：需要
- **查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string (enum) | 否 | 订单状态筛选：`intention` / `signed` / `executing` / `completed` / `cancelled` |
| sale_id | int | 否 | 销售筛选 |
| planner_id | int | 否 | 策划师筛选 |
| keyword | string | 否 | 按订单号或备注模糊搜索 |
| date_start | date | 否 | 创建日期起始 |
| date_end | date | 否 | 创建日期截止 |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 20，最大 100 |

- **响应**：分页响应
  ```json
  {
    "items": [
      {
        "id": 1,
        "order_no": "WD20260101001",
        "customer_id": 1,
        "planner_id": 2,
        "sale_id": 3,
        "status": "intention",
        "total_amount": 50000.00,
        "paid_amount": 0,
        "discount": 0.95,
        "note": "备注",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": null
      }
    ],
    "total": 50,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  }
  ```

### 2. 订单详情

- **方法**：`GET /api/v1/orders/{order_id}`
- **认证**：需要
- **路径参数**：`order_id` (int)
- **响应**：
  ```json
  {
    "id": 1,
    "order_no": "WD20260101001",
    "customer_id": 1,
    "planner_id": 2,
    "sale_id": 3,
    "status": "intention",
    "total_amount": 50000.00,
    "paid_amount": 0,
    "discount": 0.95,
    "note": "备注",
    "created_at": "2026-01-01T00:00:00",
    "updated_at": null,
    "items": [
      {
        "id": 1,
        "order_id": 1,
        "type": "venue",
        "name": "宴会厅",
        "quantity": 1,
        "unit_price": 30000.00,
        "amount": 30000.00,
        "supplier_id": 5,
        "note": null
      }
    ],
    "payments": [
      {
        "id": 1,
        "order_id": 1,
        "amount": 10000.00,
        "method": "transfer",
        "status": "confirmed",
        "paid_at": "2026-01-05T10:00:00",
        "note": "定金",
        "created_at": "2026-01-05T10:00:00"
      }
    ],
    "contract": {
      "id": 1,
      "order_id": 1,
      "file_url": "/uploads/contracts/1_20260105100000_contract.pdf",
      "status": "pending",
      "signed_at": null
    }
  }
  ```
  - `contract`：可能为 `null`（未上传合同时）
- **错误**：404 `NOT_FOUND` — 订单不存在

### 3. 创建订单

- **方法**：`POST /api/v1/orders`
- **认证**：需要
- **请求体**：
  ```json
  {
    "customer_id": 1,
    "planner_id": 2,
    "sale_id": 3,
    "discount": 0.95,
    "note": "备注",
    "items": [
      {
        "type": "venue",
        "name": "宴会厅",
        "quantity": 1,
        "unit_price": 30000.00,
        "supplier_id": 5,
        "note": null
      },
      {
        "type": "floral",
        "name": "花艺布置",
        "quantity": 1,
        "unit_price": 20000.00,
        "supplier_id": null,
        "note": null
      }
    ]
  }
  ```
  - `customer_id`（必填）、`sale_id`（必填）、`items`（必填，至少一项）为必填字段
  - 每个订单项的 `type`（必填）、`name`（必填）、`unit_price`（必填）为必填
  - `quantity` 默认 1
- **业务规则**：
  - 自动生成订单号，格式：`WD{YYYYMMDD}{NNN}`（当天序号，3位补零）
  - 订单总额 = SUM(各订单项 amount) x discount
  - 新建订单状态自动设为 `intention`
  - `paid_amount` 初始为 0
- **响应**：订单对象（同列表项格式）
- **错误**：无特殊错误（当前未校验 customer_id / sale_id 存在性）

### 4. 更新订单

- **方法**：`PUT /api/v1/orders/{order_id}`
- **认证**：需要
- **路径参数**：`order_id` (int)
- **请求体**：
  ```json
  {
    "note": "更新备注",
    "discount": 0.90,
    "planner_id": 4
  }
  ```
  - 所有字段均可选
- **业务规则**：
  - 仅 `intention`（意向）状态的订单允许修改
  - 注意：更新 discount 不会自动重算 total_amount（当前实现）
- **响应**：更新后的订单对象
- **错误**：
  - 404 `NOT_FOUND` — 订单不存在
  - 400 `INVALID_STATUS` — 仅意向状态的订单可修改

### 5. 订单状态流转

- **方法**：`PUT /api/v1/orders/{order_id}/status`
- **认证**：需要
- **路径参数**：`order_id` (int)
- **请求体**：
  ```json
  {
    "status": "signed"
  }
  ```
  - `status`（必填）：目标状态
- **业务规则**：严格的状态机校验（见下方状态机定义）
- **响应**：更新后的订单对象
- **错误**：
  - 404 `NOT_FOUND` — 订单不存在
  - 400 `INVALID_TRANSITION` — 不合法的状态转换

### 6. 记录付款

- **方法**：`POST /api/v1/orders/{order_id}/payments`
- **认证**：需要
- **路径参数**：`order_id` (int)
- **请求体**：
  ```json
  {
    "amount": 10000.00,
    "method": "transfer",
    "note": "定金"
  }
  ```
  - `amount`（必填）、`method`（必填）为必填
  - `method`：`cash` / `transfer` / `wechat` / `alipay` / `card`
- **业务规则**：
  - 校验付款后总金额不超过订单总额（`paid_amount + amount <= total_amount`）
  - 付款记录状态自动设为 `confirmed`，`paid_at` 设为当前时间
  - 更新订单的 `paid_amount`
- **响应**：付款记录对象
- **错误**：
  - 404 `NOT_FOUND` — 订单不存在
  - 400 `PAYMENT_EXCEEDS_TOTAL` — 付款金额超过订单总额

### 7. 上传合同

- **方法**：`POST /api/v1/orders/{order_id}/contract`
- **认证**：需要
- **路径参数**：`order_id` (int)
- **请求类型**：`multipart/form-data`
- **请求参数**：`file`（上传文件，必填）
- **业务规则**：
  - 文件大小限制由 `settings.MAX_FILE_SIZE_MB` 配置
  - 存储路径：`{UPLOAD_DIR}/contracts/{order_id}_{timestamp}_{filename}`
  - 若已有合同记录则更新（覆盖 file_url，状态重置为 pending，清除 signed_at）
  - 若无合同记录则新建
- **响应**：
  ```json
  {
    "id": 1,
    "order_id": 1,
    "file_url": "/uploads/contracts/1_20260105100000_contract.pdf",
    "status": "pending",
    "signed_at": null
  }
  ```
- **错误**：
  - 404 `NOT_FOUND` — 订单不存在
  - 400 `FILE_TOO_LARGE` — 文件大小超限

### 8. 生成报价单 PDF

- **方法**：`GET /api/v1/orders/{order_id}/quote-pdf`
- **认证**：需要
- **路径参数**：`order_id` (int)
- **响应**：PDF 文件流（`application/pdf`）
  - Content-Disposition: `inline; filename=quote_{order_no}.pdf`
- **PDF 内容**：
  - 标题：`Wedding Order Quote - {order_no}`
  - 客户 ID、订单状态、创建日期
  - 项目明细：名称 x 数量 @ 单价 = 金额
  - 汇总：折扣、总额、已付金额
- **错误**：404 `NOT_FOUND` — 订单不存在

## Events（领域事件）

本模块当前未显式定义领域事件。以下为隐含的状态变更，可作为后续事件驱动改造的候选：

| 隐含事件 | 触发时机 | 潜在消费方 |
|----------|---------|-----------|
| OrderCreated | 创建订单时 | Customers（更新客户状态为 intention） |
| OrderStatusChanged | 订单状态流转时 | Customers（签约后更新客户状态）、Dashboard（订单统计） |
| PaymentRecorded | 记录付款时 | Dashboard（财务统计） |
| ContractUploaded | 上传合同时 | 通知系统（通知相关人员） |
