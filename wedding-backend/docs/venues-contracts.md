# Venues 模块接口契约

## Service 接口

Venues 模块当前未定义独立的 Service 层，业务逻辑直接写在 API 路由处理函数中。

## Controller 接口（HTTP API）

基础路径：`/api/v1/venues`

### 1. 获取场地列表

- **方法**：`GET /api/v1/venues`
- **认证**：Bearer Token（必需）
- **查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 否 | 关键词搜索（匹配名称和地址） |
| capacity_min | int | 否 | 最小容量筛选 |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 20，最大 100 |

- **响应**：`PageResponse<Venue>`
```json
{
  "items": [
    {
      "id": 1,
      "name": "花嫁礼堂",
      "address": "北京市朝阳区xxx路123号",
      "capacity": 200,
      "contact": "张经理",
      "phone": "13800138000",
      "price": 50000.00,
      "note": null,
      "created_at": "2026-05-20T10:00:00",
      "updated_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

### 2. 创建场地

- **方法**：`POST /api/v1/venues`
- **认证**：Bearer Token（必需）
- **请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 场地名称（唯一） |
| address | string | 否 | 场地地址 |
| capacity | int | 否 | 容纳人数 |
| contact | string | 否 | 联系人 |
| phone | string | 否 | 联系电话 |
| price | float | 否 | 价格 |
| note | string | 否 | 备注 |

- **业务规则**：
  - 场地名称唯一，重复时返回 `400 DUPLICATE_NAME`
- **响应**：单个场地对象
- **错误**：`400 DUPLICATE_NAME` - 场地名称已存在

### 3. 更新场地

- **方法**：`PUT /api/v1/venues/{venue_id}`
- **认证**：Bearer Token（必需）
- **路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| venue_id | int | 场地 ID |

- **请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 否 | 场地名称 |
| address | string | 否 | 场地地址 |
| capacity | int | 否 | 容纳人数 |
| contact | string | 否 | 联系人 |
| phone | string | 否 | 联系电话 |
| price | float | 否 | 价格 |
| note | string | 否 | 备注 |

- **业务规则**：
  - 仅当 `name` 变更时才校验唯一性
  - 支持部分更新
- **响应**：单个场地对象
- **错误**：`404 NOT_FOUND` - 场地不存在；`400 DUPLICATE_NAME` - 场地名称已存在

### 4. 查询场地可用性

- **方法**：`GET /api/v1/venues/{venue_id}/availability`
- **认证**：Bearer Token（必需）
- **路径参数**：`venue_id` (int)
- **查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| date_start | date | 是 | 起始日期 |
| date_end | date | 是 | 结束日期 |

- **业务规则**：
  - 查询指定日期范围内已被非取消状态活动占用的日期列表
- **响应**：
```json
{
  "venue_id": 1,
  "date_start": "2026-06-01",
  "date_end": "2026-06-30",
  "booked_dates": ["2026-06-15", "2026-06-20"],
  "available": false
}
```
- **错误**：`404 NOT_FOUND` - 场地不存在

## Events（领域事件）

当前模块未显式定义领域事件。模块通过操作日志（`OperationLog`）记录写操作审计信息。
