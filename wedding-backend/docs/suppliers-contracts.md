# Suppliers 模块接口契约

## Service 接口（暴露给其他模块）

本模块目前未封装独立的 Service 层，其他模块通过数据库模型和 ID 引用关联：

- **Supplier 实体**：Orders 模块中 `OrderItem.supplier_id` 外键引用 `suppliers.id`，用于关联订单项与供应商。
- **SupplierEvaluation 实体**：通过 `order_id` 外键引用 Orders 模块，通过 `evaluator_id` 外键引用 Users 模块。
- **SupplierType 枚举**：与 Orders 模块的 `ItemType` 枚举存在对应关系（`venue`、`floral`、`photo`、`host`、`car` 值相同）。

## Controller 接口（HTTP API）

基础路径：`/api/v1/suppliers`

### 1. 供应商列表查询

- **方法**：`GET /api/v1/suppliers`
- **认证**：需要
- **查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string (enum) | 否 | 供应商类型筛选 |
| cooperation_status | string (enum) | 否 | 合作状态筛选：`active` / `suspended` / `blacklist` |
| keyword | string | 否 | 按名称、联系人或电话模糊搜索 |
| rating_min | float | 否 | 最低评分筛选 |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 20，最大 100 |

- **响应**：分页响应
  ```json
  {
    "items": [
      {
        "id": 1,
        "name": "某某花艺",
        "type": "floral",
        "contact": "王经理",
        "phone": "13800138001",
        "address": "某某路100号",
        "cooperation_status": "active",
        "rating": 4.5,
        "note": "长期合作",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": null
      }
    ],
    "total": 30,
    "page": 1,
    "page_size": 20,
    "total_pages": 2
  }
  ```

### 2. 供应商详情

- **方法**：`GET /api/v1/suppliers/{supplier_id}`
- **认证**：需要
- **路径参数**：`supplier_id` (int)
- **响应**：
  ```json
  {
    "id": 1,
    "name": "某某花艺",
    "type": "floral",
    "contact": "王经理",
    "phone": "13800138001",
    "address": "某某路100号",
    "cooperation_status": "active",
    "rating": 4.5,
    "note": "长期合作",
    "created_at": "2026-01-01T00:00:00",
    "updated_at": null,
    "services": [
      {
        "id": 1,
        "supplier_id": 1,
        "service_name": "婚礼花艺布置",
        "description": "全场花艺设计与布置",
        "price": 15000.00,
        "unit": "次",
        "note": null
      }
    ],
    "evaluations": [
      {
        "id": 1,
        "supplier_id": 1,
        "order_id": 5,
        "rating": 5,
        "content": "花艺布置非常精美",
        "evaluator_id": 3,
        "created_at": "2026-02-10T14:00:00"
      }
    ]
  }
  ```
  - `evaluations`：最多返回最近 5 条评价
- **错误**：404 `NOT_FOUND` — 供应商不存在

### 3. 创建供应商

- **方法**：`POST /api/v1/suppliers`
- **认证**：需要
- **请求体**：
  ```json
  {
    "name": "某某花艺",
    "type": "floral",
    "contact": "王经理",
    "phone": "13800138001",
    "address": "某某路100号",
    "cooperation_status": "active",
    "note": "长期合作"
  }
  ```
  - `name`（必填）、`type`（必填）为必填字段
  - `cooperation_status` 可选，默认 `active`
- **业务规则**：
  - 新建供应商评分默认为 0.0
- **响应**：供应商对象（同列表项格式）
- **错误**：无特殊错误

### 4. 更新供应商

- **方法**：`PUT /api/v1/suppliers/{supplier_id}`
- **认证**：需要
- **路径参数**：`supplier_id` (int)
- **请求体**：
  ```json
  {
    "name": "新名称",
    "type": "venue",
    "contact": "李经理",
    "phone": "13900139001",
    "address": "新地址",
    "cooperation_status": "suspended",
    "note": "暂停合作"
  }
  ```
  - 所有字段均可选，仅更新请求体中明确设置的字段
- **响应**：更新后的供应商对象
- **错误**：404 `NOT_FOUND` — 供应商不存在

### 5. 供应商服务列表

- **方法**：`GET /api/v1/suppliers/{supplier_id}/services`
- **认证**：需要
- **路径参数**：`supplier_id` (int)
- **响应**：服务对象数组
  ```json
  [
    {
      "id": 1,
      "supplier_id": 1,
      "service_name": "婚礼花艺布置",
      "description": "全场花艺设计与布置",
      "price": 15000.00,
      "unit": "次",
      "note": null
    }
  ]
  ```

### 6. 添加供应商服务

- **方法**：`POST /api/v1/suppliers/{supplier_id}/services`
- **认证**：需要
- **路径参数**：`supplier_id` (int)
- **请求体**：
  ```json
  {
    "service_name": "婚礼花艺布置",
    "description": "全场花艺设计与布置",
    "price": 15000.00,
    "unit": "次",
    "note": null
  }
  ```
  - `service_name`（必填）、`price`（必填）为必填字段
  - `unit` 可选，默认 `"次"`
- **业务规则**：验证供应商存在
- **响应**：服务对象
- **错误**：404 `NOT_FOUND` — 供应商不存在

### 7. 更新供应商服务

- **方法**：`PUT /api/v1/suppliers/{supplier_id}/services/{service_id}`
- **认证**：需要
- **路径参数**：`supplier_id` (int), `service_id` (int)
- **请求体**：
  ```json
  {
    "service_name": "新服务名",
    "description": "新描述",
    "price": 20000.00,
    "unit": "场",
    "note": "更新备注"
  }
  ```
  - 所有字段均可选
- **业务规则**：同时验证 `supplier_id` 和 `service_id` 匹配
- **响应**：更新后的服务对象
- **错误**：404 `NOT_FOUND` — 服务不存在

### 8. 添加供应商评价

- **方法**：`POST /api/v1/suppliers/{supplier_id}/evaluations`
- **认证**：需要
- **路径参数**：`supplier_id` (int)
- **请求体**：
  ```json
  {
    "order_id": 5,
    "rating": 5,
    "content": "花艺布置非常精美"
  }
  ```
  - `order_id`（必填）、`rating`（必填）为必填字段
  - `rating` 必须在 1-5 之间
- **业务规则**：
  - 验证供应商存在
  - 验证评分范围 1-5
  - 自动将 `evaluator_id` 设为当前登录用户 ID
  - 添加评价后自动重算供应商平均评分
  - 评分计算逻辑：`(当前平均分 x 当前评价数 + 新评分) / (当前评价数 + 1)`
- **响应**：评价对象
- **错误**：
  - 404 `NOT_FOUND` — 供应商不存在
  - 400 `INVALID_RATING` — 评分必须在1-5之间

### 9. 供应商评价列表

- **方法**：`GET /api/v1/suppliers/{supplier_id}/evaluations`
- **认证**：需要
- **路径参数**：`supplier_id` (int)
- **查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 20，最大 100 |

- **响应**：分页响应
  ```json
  {
    "items": [
      {
        "id": 1,
        "supplier_id": 1,
        "order_id": 5,
        "rating": 5,
        "content": "花艺布置非常精美",
        "evaluator_id": 3,
        "created_at": "2026-02-10T14:00:00"
      }
    ],
    "total": 10,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
  ```

## Events（领域事件）

本模块当前未显式定义领域事件。以下为隐含的状态变更，可作为后续事件驱动改造的候选：

| 隐含事件 | 触发时机 | 潜在消费方 |
|----------|---------|-----------|
| SupplierCreated | 创建供应商时 | Dashboard（供应商统计） |
| SupplierStatusChanged | 合作状态变更时 | Orders（检查关联订单是否受影响） |
| SupplierEvaluated | 添加供应商评价时 | Dashboard（评分排名） |
