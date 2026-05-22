# Users 模块接口契约

## Service 接口

Users 模块当前未定义独立的 Service 层，业务逻辑直接写在 API 路由处理函数中。

## Controller 接口（HTTP API）

基础路径：`/api/v1/users`

### 1. 获取用户列表

- **方法**：`GET /api/v1/users`
- **认证**：Bearer Token（必需）
- **查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| team | TeamEnum | 否 | 团队筛选（sales/planning/design/management） |
| status | UserStatus | 否 | 状态筛选（active/inactive） |
| keyword | string | 否 | 关键词搜索（匹配姓名、用户名、手机号） |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 20，最大 100 |

- **响应**：`PageResponse<User>`
```json
{
  "items": [
    {
      "id": 1,
      "username": "admin",
      "name": "管理员",
      "phone": "13800138000",
      "role_id": 1,
      "team": "management",
      "status": "active",
      "created_at": "2026-01-01T00:00:00",
      "updated_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

### 2. 创建用户

- **方法**：`POST /api/v1/users`
- **认证**：Bearer Token（必需）
- **请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名（唯一） |
| password | string | 是 | 密码（明文传入，后端 bcrypt 加密存储） |
| name | string | 是 | 真实姓名 |
| phone | string | 否 | 手机号 |
| role_id | int | 是 | 角色 ID（必须存在于 roles 表） |
| team | TeamEnum | 是 | 所属团队 |

- **业务规则**：
  - 用户名唯一，重复时返回 `400 DUPLICATE_USERNAME`
  - `role_id` 必须关联已有角色，不存在时返回 `400 INVALID_ROLE`
  - 新用户状态默认为 `active`
  - 密码使用 `bcrypt` 哈希存储
- **响应**：单个用户对象（不含密码）
- **错误**：`400 DUPLICATE_USERNAME`、`400 INVALID_ROLE`

### 3. 更新用户

- **方法**：`PUT /api/v1/users/{user_id}`
- **认证**：Bearer Token（必需）
- **路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| user_id | int | 用户 ID |

- **请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 否 | 真实姓名 |
| phone | string | 否 | 手机号 |
| role_id | int | 否 | 角色 ID |
| team | TeamEnum | 否 | 所属团队 |
| status | UserStatus | 否 | 用户状态（active/inactive） |
| password | string | 否 | 新密码（单独处理，不在普通字段更新中） |

- **业务规则**：
  - 支持部分更新
  - 若传入 `password`，单独使用 bcrypt 哈希后更新 `password_hash`
  - 若传入 `role_id`，校验角色是否存在
- **响应**：单个用户对象（不含密码）
- **错误**：`404 NOT_FOUND` - 用户不存在；`400 INVALID_ROLE` - 角色不存在

### 4. 获取角色列表

- **方法**：`GET /api/v1/users/roles`
- **认证**：Bearer Token（必需）
- **响应**：`Role[]`
```json
[
  {
    "id": 1,
    "name": "管理员",
    "display_name": "管理员",
    "permissions": ["customers:view", "customers:edit", "orders:view"]
  }
]
```

### 5. 更新角色

- **方法**：`PUT /api/v1/users/roles/{role_id}`
- **认证**：Bearer Token（必需）
- **路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| role_id | int | 角色 ID |

- **请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 否 | 角色名称 |
| permissions | list[string] | 否 | 权限列表（JSON 序列化存储） |

- **响应**：单个角色对象
- **错误**：`404 NOT_FOUND` - 角色不存在

### 6. 获取操作日志

- **方法**：`GET /api/v1/users/operation-logs`
- **认证**：Bearer Token（必需）
- **查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | int | 否 | 操作人筛选 |
| module | string | 否 | 模块筛选 |
| action | string | 否 | 操作类型筛选（create/update/delete） |
| date_start | date | 否 | 起始日期 |
| date_end | date | 否 | 结束日期 |
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页条数，默认 20，最大 100 |

- **响应**：`PageResponse<OperationLog>`
```json
{
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "user_name": "管理员",
      "module": "event",
      "action": "create",
      "target": "/api/v1/events",
      "detail": "{\"event_id\": 1, \"title\": \"张三&李四婚礼\"}",
      "ip": "127.0.0.1",
      "created_at": "2026-05-20T10:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

## Events（领域事件）

当前模块未显式定义领域事件。模块通过操作日志（`OperationLog`）记录写操作审计信息。
