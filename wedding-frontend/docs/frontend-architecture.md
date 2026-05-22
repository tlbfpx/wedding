# 前端架构分析（现状版）

## 1. 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| 框架 | Vue 3（Composition API + `<script setup>`） | ^3.5.34 |
| UI 库 | Naive UI | ^2.44.1 |
| 构建工具 | Vite | ^8.0.12 |
| 状态管理 | Pinia | ^3.0.4 |
| 路由 | Vue Router 4 | ^4.6.4 |
| HTTP 客户端 | Axios | ^1.16.1 |
| 语言 | TypeScript | ~6.0.2 |
| 图标 | @vicons/ionicons5 | ^0.13.0 |

## 2. 路由结构

所有路由在 `src/router/index.ts` 中定义，采用 `createWebHistory` 模式。

### 认证路由（无需登录）

| 路径 | 名称 | 组件 | 说明 |
|------|------|------|------|
| `/login` | Login | `views/Login.vue` | 登录页 |

### 主路由（需要登录，嵌套在 MainLayout 下）

| 路径 | 名称 | 组件 | 说明 |
|------|------|------|------|
| `/` | - | 重定向到 `/dashboard` | - |
| `/dashboard` | Dashboard | `views/Dashboard.vue` | 工作台 |
| `/customers` | Customers | `views/customers/CustomerList.vue` | 客户列表 |
| `/customers/:id` | CustomerDetail | `views/customers/CustomerDetail.vue` | 客户详情 |
| `/customer-pool` | CustomerPool | `views/customers/CustomerPool.vue` | 公海池 |
| `/events` | Events | `views/events/EventList.vue` | 排期管理 |
| `/events/:id` | EventDetail | `views/events/EventDetail.vue` | 活动详情 |
| `/venues` | Venues | `views/events/VenueList.vue` | 场地管理 |
| `/orders` | Orders | `views/Orders.vue` | 订单列表 |
| `/orders/create` | OrderCreate | `views/OrderCreate.vue` | 新建订单 |
| `/orders/:id` | OrderDetail | `views/OrderDetail.vue` | 订单详情 |
| `/suppliers` | Suppliers | `views/suppliers/SupplierList.vue` | 供应商列表 |
| `/suppliers/:id` | SupplierDetail | `views/suppliers/SupplierDetail.vue` | 供应商详情 |
| `/users` | Users | `views/system/UserList.vue` | 员工管理 |
| `/roles` | Roles | `views/system/RoleList.vue` | 角色权限 |
| `/operation-logs` | OperationLogs | `views/system/OperationLogs.vue` | 操作日志 |
| `/approvals` | Approvals | `views/Approvals.vue` | 审批管理 |

### 路由守卫

- `beforeEach`：检查 `localStorage.token`，未登录则跳转 `/login` 并携带 `redirect` 参数
- 已登录用户访问 `/login` 时重定向到 `/`

## 3. 状态管理

### auth store（`src/stores/auth.ts`）

目前前端仅有 **1 个 Pinia store**，负责认证状态管理。

| 状态/方法 | 类型 | 说明 |
|-----------|------|------|
| `token` | `ref<string>` | access token，从 localStorage 初始化 |
| `refreshTokenValue` | `ref<string>` | refresh token，从 localStorage 初始化 |
| `user` | `ref<UserInfo \| null>` | 当前登录用户信息（id, username, name, team, permissions） |
| `isLoggedIn` | `computed` | 是否已登录 |
| `permissions` | `computed` | 当前用户权限列表 |
| `login(username, password)` | `async` | 登录并获取用户信息 |
| `logout()` | `async` | 调用登出 API 并清除本地状态 |
| `fetchUser()` | `async` | 获取当前用户信息 |
| `refreshToken()` | `async` | 刷新 token |
| `hasPermission(permission)` | `function` | 权限检查 |
| `clearAuth()` | `function` | 清除所有认证状态 |

### 其他数据管理模式

其余页面数据（客户、订单、排期、供应商等）均采用 **页面级局部状态** 管理，即每个 Vue 组件内部通过 `ref`/`reactive` 维护数据，直接调用 API 函数获取，未使用全局 store。

## 4. API 调用关系（核心部分）

### 4.1 登录页（Login.vue）

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `authStore.login()` → `loginApi()` | `/api/v1/auth/login` | POST | 用户登录，获取 access_token 和 refresh_token |
| （间接）`getMeApi()` | `/api/v1/auth/me` | GET | 登录后获取当前用户信息 |

### 4.2 工作台（Dashboard.vue）

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `getOverview()` | `/api/v1/dashboard/overview` | GET | 获取工作台概览数据（订单数、营业额等） |
| `getEventList()` | `/api/v1/events` | GET | 获取近期排期列表（page_size=5） |

### 4.3 客户列表（CustomerList.vue）

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `getCustomers(params)` | `/api/v1/customers` | GET | 分页获取客户列表，支持 keyword/status/source 筛选 |
| `recycleCustomer(id)` | `/api/v1/customers/{id}/recycle` | POST | 将客户回收到公海池 |
| `transferCustomer(id, targetSaleId)` | `/api/v1/customers/{id}/transfer` | POST | 转移客户到其他销售 |
| `getUsers(params)` | `/api/v1/users` | GET | 获取销售列表（用于转移客户的目标选择） |

### 4.4 客户表单（CustomerForm.vue）— 被 CustomerList 和 CustomerDetail 引用

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `createCustomer(data)` | `/api/v1/customers` | POST | 创建客户 |
| `updateCustomer(id, data)` | `/api/v1/customers/{id}` | PUT | 更新客户信息 |
| `getCustomer(id)` | `/api/v1/customers/{id}` | GET | 编辑时获取客户详情 |

### 4.5 客户详情（CustomerDetail.vue）

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `getCustomer(id)` | `/api/v1/customers/{id}` | GET | 获取客户详情（含跟进记录） |
| `addFollowUp(customerId, data)` | `/api/v1/customers/{id}/follow-ups` | POST | 新增跟进记录 |

### 4.6 公海池（CustomerPool.vue）

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `getCustomerPool(params)` | `/api/v1/customer-pool` | GET | 分页获取公海池客户列表 |
| `claimCustomer(id)` | `/api/v1/customer-pool/{id}/claim` | POST | 认领公海池客户 |

### 4.7 排期管理（EventList.vue）

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `getEvents(params)` | `/api/v1/events` | GET | 分页获取活动列表（日历视图） |
| `createEvent(data)` | `/api/v1/events` | POST | 创建新活动 |

### 4.8 活动详情（EventDetail.vue）

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `getEvent(id)` | `/api/v1/events/{id}` | GET | 获取活动详情 |
| `updateEvent(id, data)` | `/api/v1/events/{id}` | PUT | 更新活动状态 |
| `getEventResources(eventId)` | `/api/v1/events/{id}/resources` | GET | 获取活动资源清单 |
| `addEventResource(eventId, data)` | `/api/v1/events/{id}/resources` | POST | 添加活动资源 |
| `removeEventResource(eventId, resourceId)` | `/api/v1/events/{id}/resources/{resourceId}` | DELETE | 移除活动资源 |
| `getStaffSchedule(params)` | `/api/v1/events/staff-schedule` | GET | 获取人员排期 |

### 4.9 场地管理（VenueList.vue）

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `request.get('/venues', params)` | `/api/v1/venues` | GET | 分页获取场地列表 |
| `request.post('/venues', data)` | `/api/v1/venues` | POST | 创建场地 |
| `request.put('/venues/{id}', data)` | `/api/v1/venues/{id}` | PUT | 更新场地 |
| `getEvents(params)` | `/api/v1/events` | GET | 查看场地档期时获取关联活动 |

### 4.10 订单列表（Orders.vue）

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `getOrders(params)` | `/api/v1/orders` | GET | 分页获取订单列表，支持 keyword/status/date 筛选 |

### 4.11 新建订单（OrderCreate.vue）

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `createOrder(data)` | `/api/v1/orders` | POST | 创建订单（含订单项目） |
| `getCustomers(params)` | `/api/v1/customers` | GET | 搜索客户（远程搜索，用于选择客户） |
| `getUsers(params)` | `/api/v1/users` | GET | 获取策划师列表 |
| `getSuppliers(params)` | `/api/v1/suppliers` | GET | 获取供应商列表（用于订单项目关联供应商） |

### 4.12 订单详情（OrderDetail.vue）

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `getOrder(id)` | `/api/v1/orders/{id}` | GET | 获取订单详情（含项目、收款、合同） |
| `updateOrderStatus(id, status)` | `/api/v1/orders/{id}/status` | PUT | 更新订单状态（签约/执行/完成） |
| `addPayment(orderId, data)` | `/api/v1/orders/{id}/payments` | POST | 登记收款 |
| `uploadContract(orderId, file)` | `/api/v1/orders/{id}/contract` | POST | 上传合同文件（multipart/form-data） |
| `getQuotePdf(orderId)` | `/api/v1/orders/{id}/quote-pdf` | GET | 下载报价单 PDF（responseType: blob） |
| `createApproval(data)` | `/api/v1/approvals` | POST | 提交取消订单审批 |

### 4.13 供应商列表（SupplierList.vue）

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `getSuppliers(params)` | `/api/v1/suppliers` | GET | 分页获取供应商列表，支持 type/cooperation_status/keyword 筛选 |
| `createSupplier(data)` | `/api/v1/suppliers` | POST | 创建供应商 |
| `updateSupplier(id, data)` | `/api/v1/suppliers/{id}` | PUT | 更新供应商 |

### 4.14 供应商详情（SupplierDetail.vue）

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `getSupplier(id)` | `/api/v1/suppliers/{id}` | GET | 获取供应商详情 |
| `updateSupplier(id, data)` | `/api/v1/suppliers/{id}` | PUT | 更新供应商信息 |
| `getSupplierServices(supplierId)` | `/api/v1/suppliers/{id}/services` | GET | 获取供应商服务列表 |
| `addSupplierService(supplierId, data)` | `/api/v1/suppliers/{id}/services` | POST | 添加供应商服务 |
| `updateSupplierService(supplierId, serviceId, data)` | `/api/v1/suppliers/{id}/services/{serviceId}` | PUT | 更新供应商服务 |
| `getSupplierEvaluations(supplierId, params)` | `/api/v1/suppliers/{id}/evaluations` | GET | 获取供应商评价列表 |
| `addSupplierEvaluation(supplierId, data)` | `/api/v1/suppliers/{id}/evaluations` | POST | 添加供应商评价 |

### 4.15 员工管理（UserList.vue）

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `getUsers(params)` | `/api/v1/users` | GET | 分页获取员工列表，支持 team/status/keyword 筛选 |
| `createUser(data)` | `/api/v1/users` | POST | 创建员工 |
| `updateUser(id, data)` | `/api/v1/users/{id}` | PUT | 更新员工信息 |
| `getRoles()` | `/api/v1/users/roles` | GET | 获取角色列表（用于角色选择） |

### 4.16 角色权限（RoleList.vue）

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `getRoles()` | `/api/v1/users/roles` | GET | 获取所有角色及其权限 |
| `updateRole(id, data)` | `/api/v1/users/roles/{id}` | PUT | 更新角色权限 |

### 4.17 操作日志（OperationLogs.vue）

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `getOperationLogs(params)` | `/api/v1/users/operation-logs` | GET | 分页获取操作日志，支持 user_id/module/action/date 筛选 |
| `getUsers(params)` | `/api/v1/users` | GET | 获取用户列表（用于操作人筛选） |

### 4.18 审批管理（Approvals.vue）

| API 函数 | 后端 Endpoint | HTTP 方法 | 用途 |
|----------|---------------|-----------|------|
| `getApprovals(params)` | `/api/v1/approvals` | GET | 分页获取审批列表，支持 status/type 筛选 |
| `approveApproval(id, data)` | `/api/v1/approvals/{id}` | PUT | 通过审批 |
| `rejectApproval(id, data)` | `/api/v1/approvals/{id}` | PUT | 驳回审批 |

## 5. 页面-模块映射

| 前端页面 | 前端 API 文件 | 后端 API 模块 |
|----------|---------------|---------------|
| Login | `api/auth.ts` | auth（认证模块） |
| Dashboard | `api/dashboard.ts` + `api/events.ts` | dashboard（仪表盘）+ events（排期） |
| CustomerList / CustomerDetail / CustomerForm | `api/customers.ts` + `api/users.ts` | customers（客户管理）+ users（用户） |
| CustomerPool | `api/customers.ts` | customers（客户管理 — 公海池） |
| EventList / EventDetail | `api/events.ts` | events（排期管理） |
| VenueList | `api/venues.ts` + `api/events.ts` | venues（场地管理）+ events（排期） |
| Orders / OrderCreate / OrderDetail | `api/orders.ts` + `api/customers.ts` + `api/users.ts` + `api/suppliers.ts` | orders（订单管理）+ customers + users + suppliers |
| SupplierList / SupplierDetail | `api/suppliers.ts` | suppliers（供应商管理） |
| UserList | `api/users.ts` | users（用户管理） |
| RoleList | `api/users.ts` | users（用户管理 — 角色权限） |
| OperationLogs | `api/users.ts` | users（用户管理 — 操作日志） |
| Approvals | `api/orders.ts` | orders（订单管理 — 审批） |

### API 文件与后端 Endpoint 对应关系

| 前端 API 文件 | 后端 Endpoint 前缀 | 说明 |
|---------------|-------------------|------|
| `api/auth.ts` | `/api/v1/auth/*` | 认证相关（登录、刷新、登出、获取用户信息） |
| `api/customers.ts` | `/api/v1/customers/*` + `/api/v1/customer-pool/*` | 客户管理与公海池 |
| `api/events.ts` | `/api/v1/events/*` | 排期管理 |
| `api/venues.ts` | `/api/v1/venues/*` | 场地管理 |
| `api/orders.ts` | `/api/v1/orders/*` + `/api/v1/approvals/*` | 订单管理与审批 |
| `api/suppliers.ts` | `/api/v1/suppliers/*` | 供应商管理 |
| `api/users.ts` | `/api/v1/users/*` | 用户管理、角色权限、操作日志 |
| `api/dashboard.ts` | `/api/v1/dashboard/*` | 仪表盘统计 |
| `api/approvals.ts` | `/api/v1/approvals/*` | 审批管理（独立定义，当前页面未直接使用） |

**注意**：`api/approvals.ts` 定义了独立的审批 API（`decideApproval`），但审批管理页面（`Approvals.vue`）实际从 `api/orders.ts` 导入了审批相关函数（`getApprovals`, `approveApproval`, `rejectApproval`）。两套审批 API 的接口参数结构略有差异，可能需要统一。

## 6. 认证流程

### 6.1 登录流程

```
用户输入用户名/密码
    │
    ▼
Login.vue → authStore.login(username, password)
    │
    ├── loginApi() → POST /api/v1/auth/login
    │   └── 返回 { access_token, refresh_token, token_type }
    │
    ├── setTokens() → 将 token 存入 localStorage 和 Pinia
    │
    └── fetchUser() → GET /api/v1/auth/me
        └── 返回 { id, username, name, team, permissions }
        └── 存入 authStore.user
    │
    ▼
跳转到 redirect 参数指定的页面或首页
```

### 6.2 Token 管理

- **存储位置**：`localStorage`（key: `token`、`refreshToken`）
- **传输方式**：HTTP 请求头 `Authorization: Bearer {access_token}`
- **注入时机**：Axios 请求拦截器自动从 Pinia store 读取并附加

### 6.3 Token 刷新流程

```
API 请求返回 401
    │
    ▼
响应拦截器检测到 401 + 非重试请求
    │
    ├── 无 refresh_token → 直接 logout()
    │
    ├── 正在刷新中 → 将请求加入等待队列（pendingRequests）
    │   └── 刷新成功后用新 token 重发等待的请求
    │
    └── 开始刷新
        ├── authStore.refreshToken() → POST /api/v1/auth/refresh
        │   └── 发送 { refresh_token }
        │   └── 返回新的 { access_token, refresh_token }
        ├── 更新 token → setTokens()
        ├── 重发等待队列中的请求
        └── 重发原始请求
            │
            ├── 成功 → 返回结果
            └── 失败 → logout() + 跳转登录页
```

### 6.4 401 处理流程

1. 响应拦截器捕获 401 错误
2. 检查是否有 `refreshToken`：
   - 无 → 清除认证状态，跳转登录页
   - 有 → 进入刷新流程
3. 使用互斥锁（`isRefreshing`）防止并发刷新
4. 刷新期间的请求排队等待（`pendingRequests` 数组）
5. 刷新成功：更新 token，重发所有等待请求
6. 刷新失败：清除认证状态，跳转登录页

### 6.5 登出流程

```
用户点击退出 / Token 刷新失败
    │
    ▼
authStore.logout()
    │
    ├── logoutApi() → POST /api/v1/auth/logout（失败静默忽略）
    │
    └── clearAuth()
        ├── 清除 Pinia store 中的 token、refreshToken、user
        └── 清除 localStorage 中的 token、refreshToken
    │
    ▼
跳转到 /login 页面
```
