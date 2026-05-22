# Auth 模块接口契约

## Service 接口

Auth 模块的核心服务由工具函数和中间件提供：

| 组件 | 文件位置 | 说明 |
|------|----------|------|
| `create_access_token(data)` | `app/utils/auth.py` | 生成 Access Token（JWT） |
| `create_refresh_token(data)` | `app/utils/auth.py` | 生成 Refresh Token（JWT） |
| `decode_token(token)` | `app/utils/auth.py` | 解码验证 JWT Token |
| `get_current_user(credentials, db)` | `app/middleware/auth.py` | 从请求中提取并验证当前用户 |
| `get_current_user_with_permissions(user, db)` | `app/middleware/auth.py` | 获取当前用户及其权限信息 |
| `require_permission(module, action)` | `app/middleware/auth.py` | 权限检查装饰器（工厂函数） |

### Token 工具函数

**`create_access_token(data: dict) -> str`**
- 输入：`{"sub": "<user_id>"}` 格式的字典
- 输出：JWT Access Token 字符串
- Token 包含字段：`sub`（用户 ID）、`exp`（过期时间）、`type: "access"`
- 过期时间：由配置 `settings.ACCESS_TOKEN_EXPIRE_MINUTES` 决定

**`create_refresh_token(data: dict) -> str`**
- 输入：`{"sub": "<user_id>"}` 格式的字典
- 输出：JWT Refresh Token 字符串
- Token 包含字段：`sub`（用户 ID）、`exp`（过期时间）、`type: "refresh"`
- 过期时间：由配置 `settings.REFRESH_TOKEN_EXPIRE_DAYS` 决定

**`decode_token(token: str) -> Optional[dict]`**
- 输入：JWT Token 字符串
- 输出：解码后的 payload 字典，解码失败返回 `None`

### 认证中间件

**`get_current_user`**（FastAPI Depends）
- 从 `Authorization: Bearer <token>` 提取 Token
- 检查 Token 是否在 Redis 黑名单中（`jwt:blacklist:<token>`）
- 解码验证 Token，确认 `type == "access"`
- 从数据库查询用户，确认 `status == "active"`
- 返回 `User` 对象

**`get_current_user_with_permissions`**（FastAPI Depends）
- 依赖 `get_current_user` 获取当前用户
- 从数据库查询用户的角色和权限
- 返回 `{"user": User, "permissions": dict}`

**`require_permission(module: str, action: str)`**（FastAPI Depends 工厂）
- 依赖 `get_current_user_with_permissions` 获取用户和权限
- 检查 `permissions[module][action]` 是否为 `"none"`
- 权限不足时抛出 `403 Insufficient permission`
- 返回 `ctx` 字典（含 user、permissions、scope）

## Controller 接口（HTTP API）

基础路径：`/api/v1/auth`

### 1. 登录

- **方法**：`POST /api/v1/auth/login`
- **认证**：无需认证
- **请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

- **业务规则**：
  - 登录失败计数存储在 Redis（key: `login:fail:<username>`），连续失败 5 次后锁定 30 分钟
  - 锁定时返回 `403 ACCOUNT_LOCKED`
  - 登录成功后清除失败计数
  - 仅允许 `status == "active"` 的用户登录
  - 密码使用 bcrypt 校验
- **响应**：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```
- **错误**：`403 ACCOUNT_LOCKED` - 账户已锁定；`401 INVALID_CREDENTIALS` - 用户名或密码错误

### 2. 刷新令牌

- **方法**：`POST /api/v1/auth/refresh`
- **认证**：无需认证（通过 Refresh Token 验证）
- **请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| refresh_token | string | 是 | Refresh Token |

- **业务规则**：
  - 解码 Refresh Token，验证 `type == "refresh"`
  - Token 无效或过期时返回 `401 TOKEN_EXPIRED`
  - 生成新的 Access Token 返回
- **响应**：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```
- **错误**：`401 TOKEN_EXPIRED` - 刷新令牌无效或已过期

### 3. 登出

- **方法**：`POST /api/v1/auth/logout`
- **认证**：Bearer Token（必需）
- **响应**：`{"message": "已登出"}`
- **注意**：当前实现未将 Token 加入黑名单（注释指出生产环境应从请求中获取 Token 并加入黑名单）

### 4. 获取当前用户信息

- **方法**：`GET /api/v1/auth/me`
- **认证**：Bearer Token（必需）
- **响应**：
```json
{
  "id": 1,
  "username": "admin",
  "name": "管理员",
  "phone": "13800138000",
  "team": "management",
  "status": "active",
  "permissions": {
    "customers": {"view": "all", "edit": "own"},
    "events": {"view": "all", "edit": "all"}
  }
}
```

## Events（领域事件）

Auth 模块未定义领域事件，也不记录操作日志。
