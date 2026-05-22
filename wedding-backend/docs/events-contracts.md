# Events 模块接口契约

## Service 接口

Events 模块当前未定义独立的 Service 层，业务逻辑直接写在 API 路由处理函数中。辅助函数 `_detect_conflicts` 提供冲突检测服务。

| 函数 | 说明 |
|------|------|
| `_detect_conflicts(db, venue_id, date, staff_ids, exclude_event_id)` | 检测场地和人员冲突，返回冲突描述列表 |

## Controller 接口（HTTP API）

基础路径：`/api/v1/events`

### 1. 获取活动列表

- **方法**：`GET /api/v1/events`
- **认证**：Bearer Token（必需）
- **查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| month | string | 否 | 月份筛选，格式 `YYYY-MM` |
| date_start | date | 否 | 起始日期筛选 |
| date_end | date | 否 | 结束日期筛选 |
| status | EventStatus | 否 | 状态筛选（draft/confirmed/executing/completed/cancelled） |
| planner_id | int | 否 | 策划师 ID 筛选 |
| venue_id | int | 否 | 场地 ID 筛选 |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 20，最大 200 |

- **响应**：`PageResponse<Event>`
```json
{
  "items": [
    {
      "id": 1,
      "order_id": null,
      "title": "张三&李四婚礼",
      "event_date": "2026-06-15",
      "date": "2026-06-15",
      "start_time": "09:00:00",
      "end_time": "18:00:00",
      "venue_id": 1,
      "venue": {"id": 1, "name": "花嫁礼堂"},
      "status": "draft",
      "planner_id": 2,
      "planner": {"id": 2, "name": "王策划"},
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

### 2. 获取活动详情

- **方法**：`GET /api/v1/events/{event_id}`
- **认证**：Bearer Token（必需）
- **路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| event_id | int | 活动 ID |

- **响应**：
```json
{
  "id": 1,
  "order_id": null,
  "title": "张三&李四婚礼",
  "event_date": "2026-06-15",
  "date": "2026-06-15",
  "start_time": "09:00:00",
  "end_time": "18:00:00",
  "venue_id": 1,
  "venue": {"id": 1, "name": "花嫁礼堂"},
  "status": "draft",
  "planner_id": 2,
  "planner": {"id": 2, "name": "王策划"},
  "note": null,
  "created_at": "2026-05-20T10:00:00",
  "updated_at": null,
  "resources": [
    {
      "id": 1,
      "event_id": 1,
      "resource_type": "equipment",
      "resource_id": 5,
      "quantity": 2,
      "note": null
    }
  ],
  "staff": [
    {
      "id": 1,
      "staff_id": 3,
      "event_id": 1,
      "role": "摄影师",
      "date": "2026-06-15",
      "status": "assigned"
    }
  ]
}
```
- **错误**：`404 NOT_FOUND` - 活动不存在

### 3. 创建活动

- **方法**：`POST /api/v1/events`
- **认证**：Bearer Token（必需）
- **请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_id | int | 否 | 关联订单 ID |
| title | string | 是 | 活动标题 |
| date | date | 否 | 活动日期（与 event_date 二选一） |
| event_date | string | 否 | 活动日期（前端别名，ISO 格式） |
| start_time | string | 否 | 开始时间 |
| end_time | string | 否 | 结束时间 |
| venue_id | int | 否 | 场地 ID |
| planner_id | int | 否 | 策划师 ID |
| note | string | 否 | 备注 |

- **业务规则**：
  - `date` 和 `event_date` 至少提供一个，否则返回 `400 MISSING_DATE`
  - 创建时自动检测场地冲突，存在冲突返回 `409 CONFLICT_DETECTED`
  - 新建活动状态默认为 `draft`
- **响应**：同活动列表中的单条记录
- **错误**：`400 MISSING_DATE`、`409 CONFLICT_DETECTED`

### 4. 更新活动

- **方法**：`PUT /api/v1/events/{event_id}`
- **认证**：Bearer Token（必需）
- **路径参数**：`event_id` (int)
- **请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 否 | 活动标题 |
| date | date | 否 | 活动日期 |
| start_time | string | 否 | 开始时间 |
| end_time | string | 否 | 结束时间 |
| venue_id | int | 否 | 场地 ID |
| planner_id | int | 否 | 策划师 ID |
| status | EventStatus | 否 | 活动状态 |
| note | string | 否 | 备注 |

- **业务规则**：
  - 修改 `date` 或 `venue_id` 时自动触发冲突检测
  - 使用 `exclude_event_id` 排除自身，避免误判
- **响应**：同活动列表中的单条记录
- **错误**：`404 NOT_FOUND`、`409 CONFLICT_DETECTED`

### 5. 查询员工排班

- **方法**：`GET /api/v1/events/staff-schedule`
- **认证**：Bearer Token（必需）
- **查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| date | date | 否 | 按日期筛选 |
| staff_id | int | 否 | 按员工 ID 筛选 |
| event_id | int | 否 | 按活动 ID 筛选 |

- **响应**：`StaffSchedule[]`
```json
[
  {
    "id": 1,
    "staff_id": 3,
    "event_id": 1,
    "role": "摄影师",
    "date": "2026-06-15",
    "status": "assigned"
  }
]
```

### 6. 冲突检测

- **方法**：`GET /api/v1/events/conflicts`
- **认证**：Bearer Token（必需）
- **查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| venue_id | int | 否 | 场地 ID |
| date | date | 是 | 检测日期 |
| staff_ids | string | 否 | 逗号分隔的员工 ID 列表 |
| exclude_event_id | int | 否 | 排除的活动 ID |

- **响应**：
```json
{
  "has_conflicts": true,
  "conflicts": ["场地已被占用: 张三&李四婚礼"]
}
```

### 7. 获取活动资源列表

- **方法**：`GET /api/v1/events/{event_id}/resources`
- **认证**：Bearer Token（必需）
- **路径参数**：`event_id` (int)
- **响应**：`EventResource[]`
```json
[
  {
    "id": 1,
    "event_id": 1,
    "resource_type": "equipment",
    "resource_id": 5,
    "quantity": 2,
    "note": null
  }
]
```

### 8. 添加活动资源

- **方法**：`POST /api/v1/events/{event_id}/resources`
- **认证**：Bearer Token（必需）
- **路径参数**：`event_id` (int)
- **请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| resource_type | ResourceType | 是 | 资源类型（staff/venue/vehicle/equipment/other） |
| resource_id | int | 是 | 资源 ID |
| quantity | int | 否 | 数量，默认 1 |
| note | string | 否 | 备注 |

- **响应**：单个 EventResource 对象
- **错误**：`404 NOT_FOUND` - 活动不存在

### 9. 移除活动资源

- **方法**：`DELETE /api/v1/events/{event_id}/resources/{resource_id}`
- **认证**：Bearer Token（必需）
- **路径参数**：`event_id` (int)、`resource_id` (int)
- **响应**：`{"message": "资源已移除"}`
- **错误**：`404 NOT_FOUND` - 资源不存在

## Events（领域事件）

当前模块未显式定义领域事件。模块通过操作日志（`OperationLog`）记录写操作审计信息。
