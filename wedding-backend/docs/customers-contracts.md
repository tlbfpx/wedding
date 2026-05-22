# Customers 模块接口契约

## Service 接口（暴露给其他模块）

本模块目前未封装独立的 Service 层，其他模块通过数据库模型直接关联：

- **Customer 实体**：Orders 模块通过 `customer_id` 外键引用 `customers.id`，用于关联订单与客户。
- **CustomerSource 实体**：提供客户来源字典数据，通过 `source_id` 外键被 Customer 引用。

## Controller 接口（HTTP API）

基础路径：`/api/v1`

### 1. 客户列表查询

- **方法**：`GET /api/v1/customers`
- **认证**：需要（Bearer Token）
- **查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 否 | 按姓名或手机号模糊搜索 |
| status | string (enum) | 否 | 客户状态筛选：`potential` / `following` / `intention` / `signed` / `lost` |
| source_id | int | 否 | 客户来源筛选 |
| assigned_sale_id | int | 否 | 指派销售筛选 |
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
        "name": "张三",
        "phone": "13800138000",
        "gender": "male",
        "source_id": 1,
        "status": "following",
        "budget_range": "5-10万",
        "wedding_date": "2026-10-01",
        "note": "备注",
        "assigned_sale_id": 2,
        "recycled_at": null,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": null
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  }
  ```

### 2. 客户详情

- **方法**：`GET /api/v1/customers/{customer_id}`
- **认证**：需要
- **路径参数**：`customer_id` (int)
- **响应**：
  ```json
  {
    "id": 1,
    "name": "张三",
    "phone": "13800138000",
    "gender": "male",
    "source_id": 1,
    "status": "following",
    "budget_range": "5-10万",
    "wedding_date": "2026-10-01",
    "note": "备注",
    "assigned_sale_id": 2,
    "recycled_at": null,
    "created_at": "2026-01-01T00:00:00",
    "updated_at": null,
    "follow_ups": [
      {
        "id": 1,
        "customer_id": 1,
        "sale_id": 2,
        "type": "phone",
        "content": "电话沟通，客户有意向",
        "next_follow_at": "2026-01-15T10:00:00",
        "created_at": "2026-01-10T14:30:00"
      }
    ]
  }
  ```
- **错误**：404 `NOT_FOUND` — 客户不存在

### 3. 创建客户

- **方法**：`POST /api/v1/customers`
- **认证**：需要
- **请求体**：
  ```json
  {
    "name": "张三",
    "phone": "13800138000",
    "gender": "unknown",
    "source_id": 1,
    "budget_range": "5-10万",
    "wedding_date": "2026-10-01",
    "note": "备注",
    "assigned_sale_id": 2
  }
  ```
  - `name`（必填）、`phone`（必填）为必填字段
  - `gender` 可选，默认 `unknown`
  - 其余字段均可选
- **业务规则**：
  - 手机号唯一，重复返回 400 `DUPLICATE_PHONE`
  - 新建客户状态自动设为 `potential`
- **响应**：客户对象（同列表项格式）
- **错误**：400 `DUPLICATE_PHONE` — 该手机号已存在

### 4. 更新客户

- **方法**：`PUT /api/v1/customers/{customer_id}`
- **认证**：需要
- **路径参数**：`customer_id` (int)
- **请求体**：
  ```json
  {
    "name": "李四",
    "phone": "13900139000",
    "gender": "female",
    "source_id": 2,
    "status": "following",
    "budget_range": "10-20万",
    "wedding_date": "2026-12-01",
    "note": "更新备注",
    "assigned_sale_id": 3,
    "version": 1700000000
  }
  ```
  - `version`（必填）：乐观锁版本号，基于 `updated_at` 或 `created_at` 时间戳
- **业务规则**：
  - 乐观锁校验：version 不匹配返回 409 `VERSION_CONFLICT`
  - 仅更新请求体中明确设置（非 null）的字段
- **响应**：更新后的客户对象
- **错误**：
  - 404 `NOT_FOUND` — 客户不存在
  - 409 `VERSION_CONFLICT` — 数据已被其他人修改，请刷新后重试

### 5. 添加跟进记录

- **方法**：`POST /api/v1/customers/{customer_id}/follow-ups`
- **认证**：需要
- **路径参数**：`customer_id` (int)
- **请求体**：
  ```json
  {
    "type": "phone",
    "content": "电话沟通，客户有意向",
    "next_follow_at": "2026-01-15T10:00:00"
  }
  ```
  - `type`（必填）：`phone` / `wechat` / `visit` / `other`
  - `content`（必填）：跟进内容
  - `next_follow_at`（可选）：下次跟进时间
- **业务规则**：
  - 自动将 `sale_id` 设为当前登录用户 ID
  - 若客户当前状态为 `potential`，自动变更为 `following`
- **响应**：跟进记录对象
- **错误**：404 `NOT_FOUND` — 客户不存在

### 6. 转移客户

- **方法**：`POST /api/v1/customers/{customer_id}/transfer`
- **认证**：需要
- **路径参数**：`customer_id` (int)
- **请求体**：
  ```json
  {
    "target_sale_id": 3
  }
  ```
- **业务规则**：
  - 验证目标销售存在且状态为 `active`
  - 直接修改 `assigned_sale_id` 为目标销售 ID
- **响应**：更新后的客户对象
- **错误**：
  - 404 `NOT_FOUND` — 客户不存在 / 目标销售不存在

### 7. 回收客户

- **方法**：`POST /api/v1/customers/{customer_id}/recycle`
- **认证**：需要
- **路径参数**：`customer_id` (int)
- **业务规则**：
  - 将 `assigned_sale_id` 设为 `null`（客户进入公海池）
  - 记录 `recycled_at` 时间戳
- **响应**：更新后的客户对象
- **错误**：404 `NOT_FOUND` — 客户不存在

### 8. 客户公海池列表

- **方法**：`GET /api/v1/customer-pool`
- **认证**：需要
- **查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 否 | 按姓名或手机号模糊搜索 |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 20，最大 100 |

- **业务规则**：
  - 仅返回 `assigned_sale_id` 为 `null` 的客户（未被指派的客户）
  - 按 `recycled_at` 降序排列
- **响应**：分页响应（格式同客户列表）

### 9. 认领公海池客户

- **方法**：`POST /api/v1/customer-pool/{customer_id}/claim`
- **认证**：需要
- **路径参数**：`customer_id` (int)
- **业务规则**：
  - 客户必须处于未指派状态（`assigned_sale_id` 为 `null`）
  - 将 `assigned_sale_id` 设为当前登录用户 ID
  - 清除 `recycled_at`
  - 将客户状态设为 `following`
- **响应**：更新后的客户对象
- **错误**：
  - 404 `NOT_FOUND` — 客户不存在
  - 400 `ALREADY_ASSIGNED` — 该客户已被认领

## Events（领域事件）

本模块当前未显式定义领域事件。以下为隐含的状态变更，可作为后续事件驱动改造的候选：

| 隐含事件 | 触发时机 | 潜在消费方 |
|----------|---------|-----------|
| CustomerCreated | 创建客户时 | Dashboard（统计新增客户数） |
| CustomerStatusChanged | 客户状态变更时 | Dashboard（漏斗分析） |
| CustomerTransferred | 客户转移时 | 通知系统（通知新销售） |
| CustomerRecycled | 客户回收到公海池时 | Dashboard（公海池统计） |
| CustomerClaimed | 从公海池认领客户时 | Dashboard（认领统计） |
| FollowUpCreated | 添加跟进记录时 | Dashboard（跟进统计） |
