# Users 模块设计概览

## 模块职责

Users 模块负责婚庆管理系统中**用户（员工）和角色的管理**，包括：

1. 用户（员工）的创建、查询、更新
2. 角色（含权限配置）的查询和更新
3. 操作日志的查询

该模块是系统的基础支撑模块，几乎所有模块都依赖用户信息（如活动的策划师、订单的销售人员、审批的申请人/审批人等）。

## 数据模型

### User（用户）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 用户 ID |
| username | str(50) | Unique, NOT NULL | 用户名（登录名） |
| password_hash | str(200) | NOT NULL | 密码哈希（bcrypt） |
| name | str(50) | NOT NULL | 真实姓名 |
| phone | str(20) | Nullable | 手机号 |
| role_id | int | NOT NULL | 角色 ID（逻辑外键，关联 roles 表） |
| team | TeamEnum | NOT NULL | 所属团队 |
| status | UserStatus | 默认 active | 用户状态 |
| created_at | datetime | 自动生成 | 创建时间 |
| updated_at | datetime | 自动更新 | 更新时间 |

### Role（角色）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 角色 ID |
| name | str(50) | Unique, NOT NULL | 角色名称 |
| permissions | text | NOT NULL | 权限配置（JSON 字符串） |

### OperationLog（操作日志）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 日志 ID |
| user_id | int | NOT NULL | 操作人 ID |
| module | str(30) | NOT NULL | 操作模块 |
| action | str(30) | NOT NULL | 操作类型 |
| target | str(100) | Nullable | 操作目标路径 |
| detail | text | Nullable | 操作详情（JSON） |
| ip | str(45) | Nullable | 客户端 IP |
| created_at | datetime | 自动生成 | 创建时间 |

### 枚举类型

**TeamEnum（团队枚举）**：

| 值 | 说明 |
|------|------|
| sales | 销售团队 |
| planning | 策划团队 |
| design | 设计团队 |
| management | 管理层 |

**UserStatus（用户状态）**：

| 值 | 说明 |
|------|------|
| active | 正常 |
| inactive | 停用 |

## 业务规则

### 用户管理

1. **用户名唯一**：创建和更新时均需校验用户名唯一性
2. **密码安全**：使用 bcrypt 算法进行密码哈希存储，永不明文存储
3. **密码更新**：更新密码时单独处理，`password` 字段在 `model_dump` 时被排除，仅当 `body.password` 有值时才更新 `password_hash`
4. **角色校验**：创建和更新用户时，若涉及 `role_id` 变更，必须校验角色是否存在
5. **默认状态**：新创建用户状态默认为 `active`
6. **停用用户**：将用户状态设为 `inactive` 后，该用户将无法登录认证（auth 中间件仅查询 `status == "active"` 的用户）

### 角色管理

1. **权限存储**：权限以 JSON 字符串形式存储在 `permissions` 字段中
2. **权限格式**：支持两种格式的权限数据：
   - **字典格式**（旧格式）：`{"module": {"action": "scope"}}`，如 `{"crm": {"view": "all", "edit": "own"}}`
   - **列表格式**（新格式）：`["customers:view", "customers:edit"]`
3. **权限映射**：响应时通过 `_MODULE_KEY_MAP` 将内部模块名映射为前端使用的模块名（如 `crm` → `customers`、`schedule` → `events`）
4. **权限过滤**：在字典格式中，`scope == "none"` 的权限不会出现在最终结果中

### 关键词搜索

支持按 `name`（姓名）、`username`（用户名）、`phone`（手机号）进行模糊匹配搜索，使用 SQL `LIKE` 和 OR 组合实现。

### 操作日志

1. **自动记录**：通过 `log_operation` 中间件自动记录所有写操作（POST/PUT/DELETE）
2. **模块识别**：从请求路径中自动识别操作模块（如 `/api/v1/events` → `event`）
3. **操作类型**：从 HTTP 方法映射操作类型（POST→create, PUT→update, DELETE→delete）
4. **日志查询**：支持按操作人、模块、操作类型、日期范围等多维度筛选
5. **用户名关联**：查询日志时批量加载关联用户姓名，避免 N+1 查询

## 状态机

### 用户状态

```
active ←──→ inactive
```

- `active`（正常）↔ `inactive`（停用）：通过更新接口直接切换
- 无额外状态流转约束

### 外键关系

- `Event.planner_id` → `User.id`：活动的策划师
- `Order.sale_id` → `User.id`：订单的销售人员
- `Order.planner_id` → `User.id`：订单的策划师
- `StaffSchedule.staff_id` → `User.id`：排班的员工
- `Approval.applicant_id` → `User.id`：审批申请人
- `Approval.approver_id` → `User.id`：审批人
- `User.role_id` → `Role.id`：用户的角色（逻辑外键，未声明 FK 约束）
