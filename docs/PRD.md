# 婚庆管理系统 - 产品需求文档

> **版本**: 现状版 - 基线建档
> **日期**: 2026-05-22
> **说明**: 本文档基于现有代码逆向梳理，反映系统当前实际功能状态。

---

## 1. 产品概述

婚庆管理系统是一套面向婚庆公司的全流程业务管理平台，涵盖客户获客与跟进、排期调度、场地管理、订单与合同、供应商协作、审批流程、员工权限管理等核心业务场景，旨在提升婚庆公司从获客到交付的运营效率。

---

## 2. 用户角色

| 角色 | 所属团队 | 职责说明 |
|------|----------|----------|
| 管理员 | management | 系统管理、全局配置、数据查看 |
| 销售主管 | sales | 销售团队管理、公海池分配、销售数据监控 |
| 销售 | sales | 客户跟进、订单创建、客户转移与回收 |
| 策划主管 | planning | 策划团队管理、活动排期审核 |
| 策划师 | planning | 活动策划、排期安排、资源调度 |
| 设计主管 | design | 设计团队管理 |
| 设计师 | design | 婚礼场景设计、方案制作 |

---

## 3. 功能模块总览

| 序号 | 模块 | 功能清单 | 当前状态 |
|------|------|----------|----------|
| 1 | 工作台 | 数据概览（订单数/营业额/待跟进客户/排期数）、待办事项、近期排期 | 已实现 |
| 2 | 客户管理 | 客户列表、新增/编辑客户、客户详情、跟进记录、客户转移、客户回收 | 已实现 |
| 3 | 公海池 | 公海客户列表、客户认领 | 已实现 |
| 4 | 排期管理 | 日历视图、新建活动、活动详情、资源管理、人员安排、冲突检测 | 已实现 |
| 5 | 场地管理 | 场地列表、新增/编辑场地、档期查询、场地可用性检查 | 已实现 |
| 6 | 订单管理 | 订单列表、新建订单、订单详情、订单项管理、状态流转、付款记录、合同上传、报价单 PDF 生成 | 已实现 |
| 7 | 供应商管理 | 供应商列表、新增/编辑供应商、服务项目管理、供应商评价 | 已实现 |
| 8 | 员工管理 | 员工列表、新增/编辑员工、密码重置 | 已实现 |
| 9 | 角色权限 | 角色列表、权限配置 | 已实现 |
| 10 | 审批管理 | 审批列表、折扣审批/退款审批/取消审批、审批通过/驳回 | 已实现 |
| 11 | 操作日志 | 操作日志列表、按模块/操作/用户/日期筛选 | 已实现 |
| 12 | 登录认证 | 用户登录、Token 刷新、登出、账户锁定保护 | 已实现 |

---

## 4. 各模块功能明细

### 4.1 登录认证

**功能点列表：**
- 用户名/密码登录
- JWT Access Token + Refresh Token 双令牌机制
- 登录失败 5 次后账户锁定 30 分钟（基于 Redis 计数）
- Token 刷新
- 登出
- 获取当前用户信息及权限

**页面/入口：**
- `/login` - 登录页面
- 全局路由守卫：未登录用户重定向至登录页，已登录用户访问登录页重定向至首页

**核心业务流程：**
1. 用户输入用户名密码提交登录
2. 后端校验账户状态（active）及密码（bcrypt）
3. 登录失败计数累加，达到 5 次锁定 30 分钟
4. 登录成功清除失败计数，颁发 JWT Token
5. 前端存储 Token 至 localStorage，后续请求携带 Authorization Header

**权限要求：** 无（公开接口）

---

### 4.2 工作台（Dashboard）

**功能点列表：**
- 数据概览卡片：本月订单数、营业额、待跟进客户数、本月排期数
- 待办事项列表（当前为静态数据）
- 近期排期列表（最近 5 条活动）

**页面/入口：**
- `/dashboard` - 工作台首页（登录后默认页）

**核心业务流程：**
1. 页面加载并行请求概览数据和近期排期数据
2. 概览数据按月/季/年维度统计（后端支持 period 参数）
3. 后端对概览数据做 Redis 缓存（5 分钟过期）

**权限要求：** 所有已登录用户

**后端 API：**
- `GET /api/dashboard/overview` - 概览数据（支持月/季/年维度）
- `GET /api/dashboard/sales-ranking` - 销售排行
- `GET /api/dashboard/conversion-funnel` - 客户转化漏斗
- `GET /api/dashboard/finance-summary` - 财务汇总（含支付方式分布）
- `GET /api/dashboard/schedule-heatmap` - 排期热力图
- `GET /api/dashboard/supplier-ranking` - 供应商排行

> 注：前端 Dashboard 页面当前仅使用 overview 和 events 列表接口，销售排行、转化漏斗、财务汇总、热力图、供应商排行等 API 已实现但前端未集成。

---

### 4.3 客户管理

**功能点列表：**
- 客户列表：分页浏览、按关键词（姓名/手机号）搜索、按状态筛选、按来源筛选、按日期范围筛选
- 新增客户：姓名（必填）、手机号（必填/唯一）、性别、来源、预算范围、婚期、备注、指派销售
- 编辑客户：支持乐观锁（version 字段防并发冲突）
- 客户详情：基本信息展示、跟进记录时间线
- 新增跟进记录：跟进方式（电话/微信/面访/其他）、跟进内容、下次跟进时间
- 首次跟进自动将客户状态从"潜在"变为"跟进中"
- 客户转移：将客户转给其他销售
- 客户回收：将客户回收到公海池（清空负责销售）

**页面/入口：**
- `/customers` - 客户列表页
- `/customers/:id` - 客户详情页（含基本信息 + 跟进记录）

**客户状态流转：**
```
潜在(potential) → 跟进中(following) → 有意向(intention) → 已签约(signed)
                                                                    ↓
                                                              已流失(lost)
```

**核心业务流程：**
1. 销售创建客户，状态默认为"潜在"
2. 销售添加跟进记录，状态自动转为"跟进中"
3. 销售可手动更新客户状态为"有意向"或"已签约"
4. 客户可转移给其他销售或回收到公海池
5. 回收时记录回收时间，清空负责销售

**权限要求：** 所有已登录用户可查看；创建/编辑/跟进/转移/回收需销售权限

**后端 API：**
- `GET /api/customers` - 客户列表（分页、筛选）
- `GET /api/customers/:id` - 客户详情（含跟进记录）
- `POST /api/customers` - 创建客户
- `PUT /api/customers/:id` - 更新客户（乐观锁）
- `POST /api/customers/:id/follow-ups` - 新增跟进记录
- `POST /api/customers/:id/transfer` - 转移客户
- `POST /api/customers/:id/recycle` - 回收客户到公海池

---

### 4.4 公海池

**功能点列表：**
- 公海客户列表：分页浏览、按关键词搜索、按来源筛选、按回收时间筛选
- 客户认领：销售从公海池认领客户，客户状态变为"跟进中"

**页面/入口：**
- `/customer-pool` - 公海池页面

**核心业务流程：**
1. 销售在公海池浏览未被指派的客户（assigned_sale_id 为空）
2. 点击认领后，客户指派给当前销售，状态变为"跟进中"
3. 已被认领的客户无法再次认领

**权限要求：** 销售角色

**后端 API：**
- `GET /api/customer-pool` - 公海池列表
- `POST /api/customer-pool/:id/claim` - 认领客户

---

### 4.5 排期管理

**功能点列表：**
- 日历视图：月历展示所有活动，按状态以不同颜色标记
- 日期点击侧栏：显示当日活动列表
- 新建活动：活动名称、日期、开始/结束时间、场地、策划师、备注
- 场地冲突检测：选择场地后自动检测同日冲突并警告
- 活动详情：基本信息、资源清单、人员安排
- 资源管理：添加/移除活动资源（类型、名称、数量）
- 人员排班查看
- 活动状态流转：草稿 → 已确认 → 执行中 → 已完成

**页面/入口：**
- `/events` - 排期管理（日历视图）
- `/events/:id` - 活动详情页

**活动状态流转：**
```
草稿(draft) → 已确认(confirmed) → 执行中(executing) → 已完成(completed)
```

**核心业务流程：**
1. 策划师在日历视图创建新活动，选择场地时自动检测冲突
2. 后端创建活动时执行冲突检测（场地占用 + 人员排班冲突）
3. 发现冲突返回 409 错误，前端显示冲突详情
4. 活动创建后可通过详情页逐步推进状态
5. 活动可关联订单（order_id，一对一关系）

**权限要求：** 所有已登录用户可查看；创建/编辑需策划权限

**后端 API：**
- `GET /api/events` - 活动列表（支持按月、日期范围、状态、策划师、场地筛选）
- `GET /api/events/:id` - 活动详情（含资源清单 + 人员排班）
- `POST /api/events` - 创建活动（含冲突检测）
- `PUT /api/events/:id` - 更新活动（日期/场地变更时重新检测冲突）
- `GET /api/events/staff-schedule` - 人员排班查询
- `GET /api/events/conflicts` - 冲突检测
- `GET /api/events/:id/resources` - 资源列表
- `POST /api/events/:id/resources` - 添加资源
- `DELETE /api/events/:id/resources/:resource_id` - 移除资源

---

### 4.6 场地管理

**功能点列表：**
- 场地列表：分页浏览、按关键词搜索（名称/地址）、按最小容纳人数筛选
- 新增场地：名称（必填/唯一）、地址、容纳人数、联系人、联系电话、参考价格、备注
- 编辑场地
- 档期查询：选择日期范围查看场地已有排期
- 场地可用性检查：后端查询指定日期范围内已预订日期

**页面/入口：**
- `/venues` - 场地管理页面
- 场地管理页面内嵌档期查询弹窗

**核心业务流程：**
1. 管理员/策划师维护场地基础信息
2. 在创建排期时选择场地，系统自动检测场地占用冲突
3. 在场地管理页面可直接查看指定日期范围的已有排期

**权限要求：** 所有已登录用户可查看；新增/编辑需管理或策划权限

**后端 API：**
- `GET /api/venues` - 场地列表
- `POST /api/venues` - 创建场地
- `PUT /api/venues/:id` - 更新场地
- `GET /api/venues/:id/availability` - 场地可用性检查

---

### 4.7 订单管理

**功能点列表：**
- 订单列表：分页浏览、按状态/销售/策划师/关键词/日期范围筛选
- 新建订单：选择客户（远程搜索）、选择策划师、折扣、备注、订单项（类型/名称/数量/单价/供应商/备注）
- 订单详情：基本信息、订单项列表、付款记录、合同信息
- 订单项管理：支持多种项目类型（策划/场地/花艺/摄影/主持/婚车/其他）
- 自动计算订单总额（各项金额之和 x 折扣系数）
- 折扣低于 9 折时触发审批提醒
- 订单状态流转：意向 → 已签约 → 执行中 → 已完成（可取消）
- 付款记录：金额、付款方式（现金/转账/微信/支付宝/刷卡）、自动更新已付金额
- 付款超额校验：付款总额不可超过订单总额
- 合同上传：上传合同文件（文件大小限制可配置）、覆盖已有合同
- 报价单 PDF 生成：基于 reportlab 生成 PDF 报价单
- 订单号自动生成：格式 WD{YYYYMMDD}{三位序号}

**页面/入口：**
- `/orders` - 订单列表页
- `/orders/create` - 新建订单页
- `/orders/:id` - 订单详情页

**订单状态流转：**
```
意向(intention) → 已签约(signed) → 执行中(executing) → 已完成(completed)
       ↓                  ↓                 ↓
   已取消(cancelled)  已取消(cancelled)  已取消(cancelled)
```

**核心业务流程：**
1. 销售选择客户创建意向订单，添加订单项目
2. 折扣低于 9 折时需提交折扣审批
3. 签约时上传合同文件，记录付款
4. 订单执行中可继续添加付款记录
5. 取消订单需提交取消审批

**权限要求：** 销售可创建/编辑意向订单；状态流转和付款需相应权限；取消需审批

**后端 API：**
- `GET /api/orders` - 订单列表
- `GET /api/orders/:id` - 订单详情（含订单项 + 付款记录 + 合同）
- `POST /api/orders` - 创建订单
- `PUT /api/orders/:id` - 更新订单（仅意向状态可修改）
- `PUT /api/orders/:id/status` - 状态流转
- `POST /api/orders/:id/payments` - 记录付款
- `POST /api/orders/:id/contract` - 上传合同
- `GET /api/orders/:id/quote-pdf` - 生成报价单 PDF

---

### 4.8 供应商管理

**功能点列表：**
- 供应商列表：分页浏览、按类型筛选、按合作状态筛选、按关键词搜索（名称/联系人/电话）、按最低评分筛选
- 新增供应商：名称、类型、联系人、联系电话、地址、合作状态、备注
- 编辑供应商
- 供应商详情：基本信息、服务项目列表、评价列表（最近 5 条）
- 服务项目管理：添加/编辑服务项目（名称、描述、价格、单位、备注）
- 供应商评价：关联订单评分（1-5 分）、评价内容、自动更新供应商平均评分

**供应商类型：**
- 四大金刚(four_gods)、婚车(car)、场地(venue)、花艺(floral)、摄影(photo)、主持(host)、其他(other)

**合作状态：**
- 合作中(active)、已暂停(suspended)、已拉黑(blacklist)

**页面/入口：**
- `/suppliers` - 供应商列表页
- `/suppliers/:id` - 供应商详情页

**核心业务流程：**
1. 管理员/策划师维护供应商信息和服务项目
2. 供应商关联到订单项，指定服务提供方
3. 订单完成后可对供应商进行评价
4. 评价后自动计算并更新供应商平均评分

**权限要求：** 所有已登录用户可查看；创建/编辑需管理或策划权限

**后端 API：**
- `GET /api/suppliers` - 供应商列表
- `GET /api/suppliers/:id` - 供应商详情（含服务项目 + 评价）
- `POST /api/suppliers` - 创建供应商
- `PUT /api/suppliers/:id` - 更新供应商
- `GET /api/suppliers/:id/services` - 服务项目列表
- `POST /api/suppliers/:id/services` - 添加服务项目
- `PUT /api/suppliers/:id/services/:service_id` - 更新服务项目
- `POST /api/suppliers/:id/evaluations` - 添加评价
- `GET /api/suppliers/:id/evaluations` - 评价列表（分页）

---

### 4.9 员工管理

**功能点列表：**
- 员工列表：分页浏览、按团队/状态/关键词筛选
- 新增员工：用户名（唯一）、密码、姓名、电话、角色、团队
- 编辑员工：姓名、电话、角色、团队、状态
- 密码重置
- 员工状态管理：启用(active)/停用(inactive)

**团队分类：**
- 销售(sales)、策划(planning)、设计(design)、管理(management)

**页面/入口：**
- `/users` - 员工管理页面

**核心业务流程：**
1. 管理员创建员工账号，分配角色和团队
2. 可随时修改员工信息、角色、状态
3. 停用的员工无法登录系统

**权限要求：** 管理员

**后端 API：**
- `GET /api/users` - 员工列表
- `POST /api/users` - 创建员工
- `PUT /api/users/:id` - 更新员工

---

### 4.10 角色权限

**功能点列表：**
- 角色列表
- 角色权限配置：修改角色名称、设置权限列表（JSON 格式）
- 权限格式：`{module}:{action}` 形式的权限标识

**页面/入口：**
- `/roles` - 角色权限管理页面

**核心业务流程：**
1. 管理员查看现有角色及其权限配置
2. 修改角色权限，保存后立即生效
3. 用户登录时获取其角色对应的权限列表

**权限要求：** 管理员

**后端 API：**
- `GET /api/users/roles` - 角色列表
- `PUT /api/users/roles/:id` - 更新角色权限

---

### 4.11 审批管理

**功能点列表：**
- 审批列表：分页浏览、按审批状态筛选（待审批/已通过/已驳回）、按审批类型筛选
- 审批类型：
  - 折扣审批(discount)：订单折扣低于 9 折时需审批
  - 退款审批(refund)：退款操作需审批，通过后清零已付金额
  - 取消审批(cancel)：取消订单需审批，通过后订单状态变为已取消
- 提交审批：选择类型、关联订单、填写理由
- 审批通过：记录审批人、审批备注、执行关联操作
- 审批驳回：记录审批人、驳回原因

**页面/入口：**
- `/approvals` - 审批管理页面

**审批状态流转：**
```
待审批(pending) → 已通过(approved) / 已驳回(rejected)
```

**核心业务流程：**
1. 销售提交折扣/退款/取消审批申请
2. 主管/管理员在审批列表中查看待审批项
3. 通过审批后自动执行关联操作（更新订单状态或金额）
4. 已处理的审批不可重复操作

**权限要求：** 所有用户可提交审批；审批通过/驳回需主管或管理员权限

**后端 API：**
- `GET /api/approvals` - 审批列表
- `POST /api/approvals` - 提交审批
- `PUT /api/approvals/:id` - 审批决定（通过/驳回）

---

### 4.12 操作日志

**功能点列表：**
- 操作日志列表：分页浏览、按用户/模块/操作/日期范围筛选
- 日志内容：操作人、模块、操作类型、操作目标、操作详情、IP 地址、操作时间
- 所有写操作自动记录日志（客户、订单、活动、供应商、场地、用户、角色等模块）

**页面/入口：**
- `/operation-logs` - 操作日志页面

**核心业务流程：**
1. 系统通过 `log_operation` 中间件自动记录所有写操作的日志
2. 管理员可按条件筛选查看操作历史

**权限要求：** 管理员

**后端 API：**
- `GET /api/users/operation-logs` - 操作日志列表

---

## 5. 数据实体关系

### 5.1 核心实体

| 实体 | 说明 | 关键字段 |
|------|------|----------|
| **Customer** | 客户 | name, phone(唯一), status, budget_range, wedding_date, assigned_sale_id, recycled_at |
| **FollowUp** | 跟进记录 | customer_id, sale_id, type, content, next_follow_at |
| **CustomerSource** | 客户来源 | name(唯一) |
| **Order** | 订单 | order_no(唯一), customer_id, planner_id, sale_id, status, total_amount, paid_amount, discount |
| **OrderItem** | 订单项 | order_id, type, name, quantity, unit_price, amount, supplier_id |
| **Payment** | 付款记录 | order_id, amount, method, status, paid_at |
| **Contract** | 合同 | order_id, file_url, status, signed_at |
| **Approval** | 审批 | type, target_id, applicant_id, approver_id, status, reason |
| **Event** | 活动/排期 | order_id(唯一), title, date, venue_id, planner_id, status |
| **EventResource** | 活动资源 | event_id, resource_type, resource_id, quantity |
| **StaffSchedule** | 人员排班 | staff_id, event_id, role, date, status |
| **Venue** | 场地 | name(唯一), address, capacity, price |
| **Supplier** | 供应商 | name, type, cooperation_status, rating |
| **SupplierService** | 供应商服务 | supplier_id, service_name, price, unit |
| **SupplierEvaluation** | 供应商评价 | supplier_id, order_id, rating, content, evaluator_id |
| **User** | 用户/员工 | username(唯一), password_hash, name, role_id, team, status |
| **Role** | 角色 | name(唯一), permissions(JSON) |
| **OperationLog** | 操作日志 | user_id, module, action, target, detail, ip |

### 5.2 实体关系图（文字描述）

```
Customer (1) ──── (N) FollowUp
    │                      └── Sale (User)
    │
    ├── CustomerSource (N:1)
    ├── Assigned Sale (User) (N:1)
    │
    └──── (1) ──── (N) Order
                       ├── Sale (User) (N:1)
                       ├── Planner (User) (N:1)
                       ├── (N) OrderItem ──── Supplier (N:1)
                       ├── (N) Payment
                       ├── (1) Contract
                       ├── (1) Event ──── Venue (N:1)
                       │                 ├── Planner (User) (N:1)
                       │                 ├── (N) EventResource
                       │                 └── (N) StaffSchedule ──── Staff (User) (N:1)
                       └── (N) Approval ──── Applicant (User)
                                            Approver (User)

Supplier (1) ──── (N) SupplierService
         │
         └──── (N) SupplierEvaluation ──── Order
                                           Evaluator (User)

User ──── Role (N:1)

OperationLog ──── User (N:1)
```

### 5.3 关键业务关系说明

1. **客户 → 订单**：一个客户可拥有多个订单
2. **订单 → 活动**：一个订单最多关联一个活动（一对一）
3. **订单 → 订单项**：一个订单包含多个订单项，每个订单项可关联供应商
4. **订单 → 付款**：一个订单可有多笔付款记录
5. **订单 → 合同**：一个订单最多一份合同（一对一）
6. **订单 → 审批**：一个订单可发起多次审批（折扣/退款/取消）
7. **活动 → 场地**：一个活动关联一个场地
8. **活动 → 资源**：一个活动可分配多种资源
9. **活动 → 人员排班**：一个活动可安排多名工作人员
10. **供应商 → 服务**：一个供应商提供多种服务
11. **供应商 → 评价**：一个供应商可被多次评价，评分自动计算平均值
12. **用户 → 角色**：一个用户属于一个角色，角色定义权限集合
13. **客户 → 公海池**：assigned_sale_id 为空的客户自动进入公海池
