# Auth 模块设计概览

## 模块职责

Auth 模块负责婚庆管理系统的**身份认证与授权**，包括：

1. 用户登录（用户名+密码认证）
2. JWT Token 的签发与刷新
3. Token 黑名单管理（登出）
4. 当前用户信息查询
5. 请求级身份认证（中间件）
6. 权限检查（中间件）

该模块是系统的安全基础模块，所有需要认证的 API 都依赖 Auth 中间件进行身份验证。

## 数据模型

Auth 模块不拥有独立的数据库模型，依赖 Users 模块的 `User` 和 `Role` 模型。

### 相关模型引用

| 模型 | 所属模块 | 用途 |
|------|----------|------|
| User | Users | 用户身份验证、状态检查 |
| Role | Users | 权限配置读取 |

### Token 结构

**Access Token Payload**：

| 字段 | 类型 | 说明 |
|------|------|------|
| sub | string | 用户 ID（字符串格式） |
| exp | int | 过期时间戳 |
| type | string | 固定为 `"access"` |

**Refresh Token Payload**：

| 字段 | 类型 | 说明 |
|------|------|------|
| sub | string | 用户 ID（字符串格式） |
| exp | int | 过期时间戳 |
| type | string | 固定为 `"refresh"` |

### Redis 数据结构

| Key 模式 | 类型 | 说明 |
|----------|------|------|
| `login:fail:<username>` | string(int) | 登录失败计数，TTL 1800 秒（30 分钟） |
| `jwt:blacklist:<token>` | string | Token 黑名单（当前未完全实现） |

## 业务规则

### 登录认证

1. **账户锁定机制**：
   - 使用 Redis 记录每个用户名的登录失败次数
   - 连续失败 5 次后锁定账户 30 分钟
   - 锁定期间即使密码正确也无法登录
   - 登录成功后立即清除失败计数
2. **密码验证**：使用 `bcrypt.checkpw` 对比明文密码与存储的哈希值
3. **用户状态检查**：仅 `status == "active"` 的用户可登录
4. **Token 签发**：登录成功后同时签发 Access Token 和 Refresh Token

### Token 刷新

1. **Token 类型校验**：仅接受 `type == "refresh"` 的 Token 进行刷新
2. **Token 过期校验**：通过 `decode_token` 验证 Token 是否有效且未过期
3. **新 Token 签发**：刷新时仅签发新的 Access Token，不签发新的 Refresh Token

### 身份认证中间件

1. **Token 提取**：从 `Authorization: Bearer <token>` 请求头提取 Token
2. **黑名单检查**：检查 Token 是否在 Redis 黑名单中（`jwt:blacklist:<token>`）
3. **Token 解码**：解码验证 JWT，确认 `type == "access"`
4. **用户加载**：从数据库查询用户，确认用户存在且 `status == "active"`
5. **返回值**：返回 `User` ORM 对象，可供后续路由处理函数直接使用

### 权限检查

1. **权限数据结构**：角色权限以 JSON 字典形式存储，格式为 `{module: {action: scope}}`
2. **权限匹配**：检查 `permissions[module][action]` 的值
3. **权限范围**：
   - `"none"`：无权限，拒绝访问
   - 其他值（如 `"all"`、`"own"`）：有权限，scope 值附加到上下文
4. **模块映射**：权限键使用内部模块名（如 `crm`、`schedule`），需与 `_MODULE_KEY_MAP` 对应

### 登出

1. **当前实现**：仅返回成功消息，未实现 Token 黑名单写入
2. **预期行为**：应将当前请求的 Token 写入 Redis 黑名单，使其失效

## 状态机

Auth 模块无状态机设计。认证流程为无状态请求-响应模式，基于 JWT Token 进行身份验证。

### Token 生命周期

```
登录 → 签发 Access Token + Refresh Token
         │                        │
         │ Access Token 过期      │ Refresh Token 有效
         │ ──────────────────────→ 刷新签发新 Access Token
         │                        │
         │                        │ Refresh Token 过期
         │                        │ ──→ 需重新登录
         │
         │ 用户登出
         │ ──→ Token 加入黑名单（待实现）
```
