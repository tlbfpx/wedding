# 架构优化方案

> 基于基线建档分析，针对三个核心架构问题进行优化设计
> 分支：refactor/extract-service-layer-decouple-approval

---

## 1. 现状问题

### 1.1 业务逻辑耦合在路由层

当前所有模块的业务逻辑直接内联在 FastAPI 路由处理函数中，路由文件既负责 HTTP 参数解析/响应序列化，又负责业务规则校验和数据持久化。具体问题分布如下：

**orders 模块** (`api/orders.py`, ~493 行)：
- `create_order`：订单号生成（`_generate_order_no`）、订单项金额计算、折扣计算、订单创建全部内联
- `transition_status`：状态流转校验（`VALID_TRANSITIONS` 规则定义在模块顶层）、状态变更
- `record_payment`：付款金额校验（超额检查）、付款记录创建、已付金额更新
- `upload_contract`：文件大小校验、文件存储路径拼接、合同记录创建/更新
- `generate_quote_pdf`：PDF 生成逻辑（reportlab）完全内联在路由中
- `_generate_order_no`、`_order_to_dict` 等 Helper 函数与路由同级，无封装

**customers 模块** (`api/customers.py`, ~357 行)：
- `create_customer`：手机号唯一性校验、客户创建
- `update_customer`：乐观锁校验（版本号比对）、字段更新
- `add_follow_up`：首次跟进自动变更客户状态（potential -> following）
- `transfer_customer`：目标销售存在性校验、客户转移
- `recycle_customer`：回收至公海池逻辑
- `claim_customer`：认领校验（是否已被认领）、状态变更

**events 模块** (`api/events.py`, ~436 行)：
- `create_event`：日期解析、冲突检测调用、活动创建
- `update_event`：变更冲突检测（仅 date/venue 变更时触发）、字段更新
- `_detect_conflicts`：场地冲突查询 + 人员冲突查询，纯业务逻辑放在 Helper 中
- `_event_to_dict`：序列化时额外查询 Venue 和 User 名称（N+1 问题隐患）

**suppliers 模块** (`api/suppliers.py`, ~373 行)：
- `add_evaluation`：评分范围校验（1-5）、评分重算平均值逻辑内联
- `_supplier_to_dict` 等序列化函数与路由同级

**approvals 模块** (`api/approvals.py`, ~209 行)：
- `decide_approval`：审批状态校验、审批决策执行（`_execute_approval_action`）
- `_execute_approval_action`：**直接操作 Order 模型**（跨模块耦合的核心问题，详见 1.2）

**users 模块** (`api/users.py`, ~322 行)：
- `create_user`：用户名唯一性校验、角色存在性校验、密码哈希
- `update_user`：角色存在性校验、密码重置哈希
- `_role_to_dict`：权限格式转换逻辑（dict -> list 映射）较复杂，放在 Helper 中

**dashboard 模块** (`api/dashboard.py`, ~300 行)：
- 所有统计查询直接内联在路由函数中，无复用性
- Redis 缓存逻辑与查询逻辑混合

### 1.2 审批-订单强耦合

`api/approvals.py` 中的 `_execute_approval_action` 函数直接 import 并操作 Order 模型：

```python
async def _execute_approval_action(db: AsyncSession, approval: Approval):
    if approval.type == ApprovalType.cancel:
        result = await db.execute(select(Order).where(Order.id == approval.target_id))
        order = result.scalar_one_or_none()
        if order:
            order.status = OrderStatus.cancelled    # 直接修改订单状态

    elif approval.type == ApprovalType.refund:
        result = await db.execute(select(Order).where(Order.id == approval.target_id))
        order = result.scalar_one_or_none()
        if order:
            order.paid_amount = 0                    # 直接修改订单金额
```

**问题**：
1. **违反单一职责**：审批模块需要了解订单的状态枚举（`OrderStatus`）和业务规则
2. **双向依赖风险**：approvals 依赖 orders 的模型和枚举，orders 也有可能需要查询审批状态
3. **扩展性差**：新增审批类型（如"延期审批"）需要修改审批模块和订单模块的代码
4. **难以测试**：审批逻辑的单元测试必须依赖 Order 模型和数据库
5. **事务边界不清晰**：审批状态更新和订单状态变更是同一个 `db.commit()`，回滚策略耦合

### 1.3 缺少领域事件

当前模块间通信全部通过**同步数据库操作**实现，缺乏松耦合的事件通知机制：

| 现有联动 | 问题 |
|----------|------|
| 审批通过 -> 直接修改订单状态/金额 | 审批模块与订单模块强耦合 |
| 首次跟进 -> 客户状态变为 following | 状态变更逻辑内联在跟进流程中，无法被其他场景复用 |
| 供应商评价 -> 重算平均评分 | 评分更新逻辑内联在评价路由中，如果未来有批量导入评价则需重复实现 |
| Dashboard 聚合查询 | 每次请求全量查询，只能通过 Redis 缓存缓解，无法基于事件做增量更新 |

**缺失能力**：
- 无法在不修改已有代码的情况下扩展业务联动（违反开闭原则）
- 无法记录业务事件流用于审计或数据同步
- 无法在事务提交后执行副作用（如发送通知），当前所有副作用都在事务内

---

## 2. 目标架构

### 2.1 Service 层设计

#### 总体原则

- 路由层（`api/`）：只负责 HTTP 参数解析、调用 Service、构造 HTTP 响应
- Service 层（`services/`）：封装业务逻辑，接收 primitive 参数或 Schema 对象，返回 ORM 对象或 dict
- 数据层（`models/`）：保持不变，ORM 模型定义
- Service 通过 `AsyncSession` 直接操作数据库，不引入额外的 Repository 层（避免过度设计）

#### 各模块 Service 类设计

##### OrderService (`services/order_service.py`)

```python
class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_orders(self, filters: dict, page: int, page_size: int) -> PageResult
    async def get_order_detail(self, order_id: int) -> OrderDetail
    async def create_order(self, data: OrderCreate, user_id: int) -> Order
    async def update_order(self, order_id: int, data: OrderUpdate) -> Order
    async def transition_status(self, order_id: int, new_status: OrderStatus) -> Order
    async def record_payment(self, order_id: int, data: PaymentCreate) -> Payment
    async def upload_contract(self, order_id: int, file: UploadFile) -> Contract
    async def generate_quote_pdf(self, order_id: int) -> BytesIO
    async def cancel_order(self, order_id: int) -> Order          # 新增：供事件处理器调用
    async def refund_order(self, order_id: int) -> Order           # 新增：供事件处理器调用
    async def generate_order_no(self) -> str                       # 提取订单号生成逻辑
```

**抽取的业务逻辑**：
- 订单号生成规则（`WD{YYYYMMDD}{seq}`）
- 订单项金额计算 + 折扣计算
- 状态流转校验（`VALID_TRANSITIONS` 规则移入 Service）
- 付款超额校验
- 合同文件存储路径拼接
- PDF 报价单生成
- 订单取消/退款操作（供审批事件消费者调用）

##### CustomerService (`services/customer_service.py`)

```python
class CustomerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_customers(self, filters: dict, page: int, page_size: int) -> PageResult
    async def get_customer_detail(self, customer_id: int) -> CustomerDetail
    async def create_customer(self, data: CustomerCreate) -> Customer
    async def update_customer(self, customer_id: int, data: CustomerUpdate) -> Customer
    async def add_follow_up(self, customer_id: int, data: FollowUpCreate, user_id: int) -> FollowUp
    async def transfer_customer(self, customer_id: int, target_sale_id: int) -> Customer
    async def recycle_customer(self, customer_id: int) -> Customer
    async def list_customer_pool(self, filters: dict, page: int, page_size: int) -> PageResult
    async def claim_customer(self, customer_id: int, user_id: int) -> Customer
```

**抽取的业务逻辑**：
- 手机号唯一性校验
- 乐观锁版本号校验
- 首次跟进自动变更客户状态（potential -> following）
- 公海池认领校验（是否已被认领）
- 目标销售存在性校验

##### EventService (`services/event_service.py`)

```python
class EventService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_events(self, filters: dict, page: int, page_size: int) -> PageResult
    async def get_event_detail(self, event_id: int) -> EventDetail
    async def create_event(self, data: EventCreate) -> Event
    async def update_event(self, event_id: int, data: EventUpdate) -> Event
    async def query_staff_schedule(self, filters: dict) -> list[StaffSchedule]
    async def check_conflicts(self, venue_id: int, date: date, staff_ids: list[int], exclude_event_id: int) -> list[str]
    async def add_resource(self, event_id: int, data: ResourceInput) -> EventResource
    async def remove_resource(self, event_id: int, resource_id: int) -> None
    async def detect_conflicts(self, venue_id, date, staff_ids, exclude_event_id) -> list[str]  # 内部方法
```

**抽取的业务逻辑**：
- 日期解析（`event_date` alias 处理）
- 冲突检测（场地冲突 + 人员冲突）
- 冲突异常抛出

##### SupplierService (`services/supplier_service.py`)

```python
class SupplierService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_suppliers(self, filters: dict, page: int, page_size: int) -> PageResult
    async def get_supplier_detail(self, supplier_id: int) -> SupplierDetail
    async def create_supplier(self, data: SupplierCreate) -> Supplier
    async def update_supplier(self, supplier_id: int, data: SupplierUpdate) -> Supplier
    async def list_services(self, supplier_id: int) -> list[SupplierService]
    async def add_service(self, supplier_id: int, data: ServiceCreate) -> SupplierService
    async def update_service(self, supplier_id: int, service_id: int, data: ServiceUpdate) -> SupplierService
    async def add_evaluation(self, supplier_id: int, data: EvaluationCreate, user_id: int) -> SupplierEvaluation
    async def list_evaluations(self, supplier_id: int, page: int, page_size: int) -> PageResult
    async def recalculate_rating(self, supplier_id: int) -> None                    # 内部方法
```

**抽取的业务逻辑**：
- 评分范围校验（1-5）
- 评分平均值重算逻辑
- 供应商存在性校验

##### ApprovalService (`services/approval_service.py`)

```python
class ApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_approvals(self, filters: dict, page: int, page_size: int) -> PageResult
    async def create_approval(self, data: ApprovalCreate, user_id: int) -> Approval
    async def decide_approval(self, approval_id: int, decision: ApprovalDecision, user_id: int) -> Approval
    async def _validate_decision(self, approval: Approval, new_status: ApprovalStatus) -> None  # 内部方法
```

**抽取的业务逻辑**：
- 审批状态校验（已处理不可再处理、不能设为 pending）
- 审批决策执行——**不再直接操作 Order**，改为发布领域事件（详见 2.2）

##### UserService (`services/user_service.py`)

```python
class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(self, filters: dict, page: int, page_size: int) -> PageResult
    async def create_user(self, data: UserCreate) -> User
    async def update_user(self, user_id: int, data: UserUpdate) -> User
    async def list_roles(self) -> list[Role]
    async def update_role(self, role_id: int, data: RoleUpdate) -> Role
    async def list_operation_logs(self, filters: dict, page: int, page_size: int) -> PageResult
```

**抽取的业务逻辑**：
- 用户名唯一性校验
- 角色存在性校验
- 密码哈希生成

#### Service 与路由层的关系

```python
# 路由层改造后的示例（orders）
@router.post("")
async def create_order(
    body: OrderCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = OrderService(db)
    order = await service.create_order(body, user.id)
    await log_operation(db, user.id, request, {"order_id": order.id, "order_no": order.order_no})
    return _order_to_dict(order)
```

路由层保留的职责：
- 参数解析（Query、Body、Path、File）
- 认证依赖注入（`Depends(get_current_user)`）
- 操作日志记录（`log_operation`）
- 响应序列化（`_xxx_to_dict`）

#### Service 与数据层的关系

- Service 构造函数接收 `AsyncSession`，直接通过 Session 操作 ORM
- 不引入 Repository 层，避免过度抽象
- Service 方法负责开启/管理事务边界（通过 `db.commit()` / `db.flush()`）

### 2.2 事件驱动设计

#### 事件总线实现方案

采用**进程内同步事件总线**，不引入消息队列（MQ），保持部署简单。

```python
# app/events/__init__.py

from typing import Callable, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DomainEvent:
    """领域事件基类"""
    event_type: str
    payload: dict


class EventBus:
    """进程内同步事件总线"""

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent):
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {event.event_type}, handler: {handler.__name__}, error: {e}")
                raise


# 全局单例
event_bus = EventBus()
```

**设计决策**：
- 同步执行：事件处理器在发布者的请求上下文中同步执行，共享同一个 `AsyncSession`，保证事务一致性
- 异常冒泡：处理器抛出异常会导致整个请求事务回滚
- 简单注册：模块在初始化时通过 `event_bus.subscribe()` 注册处理器
- 不引入 MQ：当前为单体应用，进程内事件足够；未来需要时再替换为异步 MQ

#### 事件定义

```python
# app/events/event_types.py

# ── 审批相关事件 ──
APPROVAL_APPROVED = "approval.approved"      # 审批通过
APPROVAL_REJECTED = "approval.rejected"      # 审批驳回

# ── 订单相关事件 ──
ORDER_CREATED = "order.created"              # 订单创建
ORDER_STATUS_CHANGED = "order.status_changed"  # 订单状态变更
ORDER_CANCELLED = "order.cancelled"          # 订单取消
ORDER_REFUNDED = "order.refunded"            # 订单退款

# ── 客户相关事件 ──
CUSTOMER_STATUS_CHANGED = "customer.status_changed"  # 客户状态变更

# ── 供应商相关事件 ──
SUPPLIER_EVALUATED = "supplier.evaluated"    # 供应商被评价
```

#### 事件载荷格式

```python
# 审批通过事件载荷
{
    "approval_id": 1,
    "approval_type": "cancel",       # cancel / discount / refund
    "target_id": 42,                  # 关联的订单 ID
    "approver_id": 3,
}

# 订单状态变更事件载荷
{
    "order_id": 42,
    "old_status": "intention",
    "new_status": "signed",
}

# 客户状态变更事件载荷
{
    "customer_id": 10,
    "old_status": "potential",
    "new_status": "following",
    "trigger": "first_follow_up",     # 触发原因
}
```

#### 事件订阅关系

| 事件 | 发布方 | 订阅方 | 处理行为 |
|------|--------|--------|----------|
| `approval.approved` | ApprovalService | OrderService | 根据 approval_type 执行 cancel_order 或 refund_order |
| `approval.rejected` | ApprovalService | （暂无，预留） | - |
| `order.status_changed` | OrderService | （暂无，预留） | - |
| `customer.status_changed` | CustomerService | （暂无，预留） | - |
| `supplier.evaluated` | SupplierService | （暂无，预留） | - |

**核心解耦**：审批通过后不再直接修改 Order，而是发布 `approval.approved` 事件，由 OrderService 的处理器订阅并执行订单状态变更。

#### 事件处理器注册

```python
# app/events/handlers.py

from app.events import event_bus, DomainEvent
from app.events.event_types import APPROVAL_APPROVED


async def on_approval_approved(event: DomainEvent):
    """审批通过 -> 执行关联操作"""
    from app.database import async_session_factory
    from app.services.order_service import OrderService
    from app.models.order import ApprovalType

    approval_type = event.payload["approval_type"]
    target_id = event.payload["target_id"]

    # 注意：如果与发布者共享 session，则不需要新建 session
    # 这里通过参数传递 session，在注册时绑定
    ...


def register_event_handlers():
    """应用启动时调用，注册所有事件处理器"""
    event_bus.subscribe(APPROVAL_APPROVED, on_approval_approved)
```

**事务策略**：事件处理器与发布者共享同一个 `AsyncSession`，在同一个请求事务中执行。如果事件处理器需要独立事务（如发送通知），后续可扩展 `publish_async` 方法支持。

### 2.3 审批-订单解耦

#### 改造前（现状）

```
ApprovalService.decide_approval()
    ├── 更新 Approval 状态
    ├── _execute_approval_action()
    │   ├── 查询 Order（import from app.models.order）
    │   ├── if cancel: order.status = OrderStatus.cancelled
    │   └── if refund: order.paid_amount = 0
    └── db.commit()  ← 审批和订单变更在同一事务
```

#### 改造后

```
ApprovalService.decide_approval()
    ├── 更新 Approval 状态
    ├── event_bus.publish(ApprovalApproved)
    │   └── [同步调用] OrderApprovalHandler.handle()
    │       ├── OrderService.cancel_order()  或  OrderService.refund_order()
    │       └── （Order 模块的内部逻辑，审批模块无需知晓）
    └── db.commit()  ← 仍在同一事务，保证一致性
```

**关键变化**：
1. `ApprovalService` 不再 import `Order` 和 `OrderStatus`
2. `ApprovalService` 只负责审批自身的状态管理 + 发布事件
3. `OrderService` 提供 `cancel_order()` 和 `refund_order()` 方法，由事件处理器调用
4. 事务仍然一致：事件处理器在发布者的 session 中同步执行

---

## 3. 目录结构变更

### 3.1 重构前

```
wedding-backend/app/
├── api/                          # 路由层（业务逻辑内联）
│   ├── auth.py
│   ├── customers.py              # 包含所有客户业务逻辑
│   ├── orders.py                 # 包含所有订单业务逻辑
│   ├── approvals.py              # 包含审批逻辑 + 直接操作 Order
│   ├── events.py                 # 包含活动逻辑 + 冲突检测
│   ├── suppliers.py              # 包含供应商逻辑 + 评分计算
│   ├── users.py                  # 包含用户管理逻辑
│   ├── venues.py
│   └── dashboard.py              # 包含聚合查询 + Redis 缓存
├── middleware/
│   ├── auth.py
│   └── logging.py
├── models/                       # 数据模型层
│   ├── base.py
│   ├── user.py
│   ├── customer.py
│   ├── order.py
│   ├── event.py
│   ├── supplier.py
│   └── log.py
├── schemas/                      # 空目录（预留）
├── services/                     # 空目录（预留）
├── utils/
│   ├── auth.py
│   ├── cache.py
│   ├── errors.py
│   └── pagination.py
├── config.py
├── database.py
├── main.py
└── seed.py
```

### 3.2 重构后

```
wedding-backend/app/
├── api/                          # 路由层（薄层，仅做参数解析和响应序列化）
│   ├── auth.py                   # 不变（认证逻辑简单，无需 Service）
│   ├── customers.py              # 精简：参数解析 -> CustomerService 调用 -> 响应
│   ├── orders.py                 # 精简：参数解析 -> OrderService 调用 -> 响应
│   ├── approvals.py              # 精简 + 移除 _execute_approval_action
│   ├── events.py                 # 精简：参数解析 -> EventService 调用 -> 响应
│   ├── suppliers.py              # 精简：参数解析 -> SupplierService 调用 -> 响应
│   ├── users.py                  # 精简：参数解析 -> UserService 调用 -> 响应
│   ├── venues.py                 # 不变（CRUD 简单，暂不抽取）
│   └── dashboard.py              # 暂不重构（只读聚合，独立性强）
├── events/                       # 新增：事件机制
│   ├── __init__.py               # EventBus、DomainEvent 定义
│   ├── event_types.py            # 事件类型常量
│   └── handlers.py               # 事件处理器 + 注册函数
├── middleware/
│   ├── auth.py
│   └── logging.py
├── models/                       # 数据模型层（不变）
│   ├── base.py
│   ├── user.py
│   ├── customer.py
│   ├── order.py
│   ├── event.py
│   ├── supplier.py
│   └── log.py
├── schemas/                      # 新增：Pydantic Schema 定义
│   ├── __init__.py
│   ├── order.py                  # OrderCreate, OrderUpdate, PaymentCreate 等
│   ├── customer.py               # CustomerCreate, CustomerUpdate, FollowUpCreate 等
│   ├── event.py                  # EventCreate, EventUpdate, ResourceInput 等
│   ├── supplier.py               # SupplierCreate, SupplierUpdate, EvaluationCreate 等
│   ├── approval.py               # ApprovalCreate, ApprovalDecision
│   └── user.py                   # UserCreate, UserUpdate, RoleUpdate
├── services/                     # 新增：业务逻辑层
│   ├── __init__.py
│   ├── order_service.py
│   ├── customer_service.py
│   ├── event_service.py
│   ├── supplier_service.py
│   ├── approval_service.py
│   └── user_service.py
├── utils/
│   ├── auth.py
│   ├── cache.py
│   ├── errors.py
│   └── pagination.py
├── config.py
├── database.py
├── main.py                       # 增加：事件处理器注册
└── seed.py
```

---

## 4. 分模块重构任务

### 4.1 基础设施（先完成）

- [ ] **创建事件总线基础设施**
  - 创建 `app/events/__init__.py`：实现 `EventBus` 类、`DomainEvent` 数据类、全局 `event_bus` 单例
  - 创建 `app/events/event_types.py`：定义所有事件类型常量
  - 创建 `app/events/handlers.py`：实现事件处理器骨架 + `register_event_handlers()` 函数
  - 修改 `app/main.py`：在应用启动时调用 `register_event_handlers()`
  - **Commit**: `feat(events): add domain event bus infrastructure`

- [ ] **提取 Pydantic Schema 到独立文件**
  - 创建 `app/schemas/order.py`：从 `api/orders.py` 迁移 `OrderItemInput`、`OrderCreate`、`OrderUpdate`、`StatusTransition`、`PaymentCreate`
  - 创建 `app/schemas/customer.py`：从 `api/customers.py` 迁移 `CustomerCreate`、`CustomerUpdate`、`FollowUpCreate`、`TransferRequest`
  - 创建 `app/schemas/event.py`：从 `api/events.py` 迁移 `EventCreate`、`EventUpdate`、`ResourceInput`、`ConflictCheck`
  - 创建 `app/schemas/supplier.py`：从 `api/suppliers.py` 迁移 `SupplierCreate`、`SupplierUpdate`、`ServiceCreate`、`ServiceUpdate`、`EvaluationCreate`
  - 创建 `app/schemas/approval.py`：从 `api/approvals.py` 迁移 `ApprovalCreate`、`ApprovalDecision`
  - 创建 `app/schemas/user.py`：从 `api/users.py` 迁移 `UserCreate`、`UserUpdate`、`RoleUpdate`
  - 修改各 `api/*.py`：改为 `from app.schemas.xxx import ...`
  - **Commit**: `refactor(schemas): extract Pydantic schemas from route files`

### 4.2 各模块任务（按依赖顺序）

#### OrderService（优先，被审批解耦依赖）

- [ ] **创建 OrderService**
  - 创建 `app/services/order_service.py`
  - 抽取以下业务逻辑到 Service 方法：
    - `generate_order_no()`：订单号生成规则（从 `_generate_order_no` 迁移）
    - `list_orders()`：查询构建 + 分页（从 `list_orders` 路由迁移）
    - `get_order_detail()`：订单详情查询（含 items、payments、contract）
    - `create_order()`：订单项金额计算、折扣计算、订单创建（从 `create_order` 路由迁移）
    - `update_order()`：状态校验（仅意向可改）、字段更新（从 `update_order` 路由迁移）
    - `transition_status()`：状态流转校验（`VALID_TRANSITIONS` 移入 Service）、状态变更
    - `record_payment()`：付款超额校验、付款记录创建、已付金额更新
    - `upload_contract()`：文件校验、存储路径拼接、合同记录创建/更新
    - `generate_quote_pdf()`：PDF 生成逻辑（从路由迁移 reportlab 代码）
    - `cancel_order()`：新增方法，设置 `order.status = OrderStatus.cancelled`，发布 `ORDER_CANCELLED` 事件
    - `refund_order()`：新增方法，设置 `order.paid_amount = 0`，发布 `ORDER_REFUNDED` 事件
  - **Commit**: `feat(orders): extract OrderService with business logic`

- [ ] **精简 orders 路由层**
  - 修改 `api/orders.py`：所有路由函数改为调用 `OrderService` 方法
  - 路由层只保留：参数解析（Depends）、操作日志（`log_operation`）、响应序列化（`_xxx_to_dict`）
  - 移除 `VALID_TRANSITIONS` 顶层常量（移入 Service）
  - 移除 `_generate_order_no` 函数（移入 Service）
  - **Commit**: `refactor(orders): slim down route handlers to call OrderService`

#### ApprovalService + 审批-订单解耦

- [ ] **创建 ApprovalService 并实现事件发布**
  - 创建 `app/services/approval_service.py`
  - 抽取以下业务逻辑到 Service 方法：
    - `list_approvals()`：查询构建 + 分页 + 用户/订单名称关联查询
    - `create_approval()`：审批记录创建
    - `decide_approval()`：审批状态校验、决策执行
    - `_validate_decision()`：审批决策校验（已处理不可再处理等）
  - **关键变更**：`decide_approval` 中不再调用 `_execute_approval_action`，改为：
    ```python
    if body.status == ApprovalStatus.approved:
        await event_bus.publish(DomainEvent(
            event_type=APPROVAL_APPROVED,
            payload={
                "approval_id": approval.id,
                "approval_type": approval.type.value,
                "target_id": approval.target_id,
                "approver_id": user_id,
            }
        ))
    ```
  - 移除 `_execute_approval_action` 函数
  - 移除 `from app.models.order import Order, OrderStatus` 导入
  - **Commit**: `feat(approvals): extract ApprovalService with event publishing`

- [ ] **实现审批事件处理器**
  - 在 `app/events/handlers.py` 中实现 `on_approval_approved` 处理器：
    - 根据 `approval_type` 调用 `OrderService.cancel_order()` 或 `OrderService.refund_order()`
    - 处理器接收 `AsyncSession` 参数，复用发布者的事务
  - 在 `register_event_handlers()` 中注册处理器
  - **Commit**: `feat(events): implement approval event handler for order decoupling`

- [ ] **精简 approvals 路由层**
  - 修改 `api/approvals.py`：所有路由函数改为调用 `ApprovalService` 方法
  - 移除 `_execute_approval_action` 函数
  - 移除 `from app.models.order import Order, OrderStatus` 导入
  - **Commit**: `refactor(approvals): slim down route handlers to call ApprovalService`

#### CustomerService

- [ ] **创建 CustomerService**
  - 创建 `app/services/customer_service.py`
  - 抽取以下业务逻辑到 Service 方法：
    - `list_customers()`：查询构建 + 分页
    - `get_customer_detail()`：客户详情 + 最近跟进记录
    - `create_customer()`：手机号唯一性校验、客户创建
    - `update_customer()`：乐观锁校验、字段更新
    - `add_follow_up()`：跟进记录创建、首次跟进自动变更状态（potential -> following）
    - `transfer_customer()`：目标销售存在性校验、客户转移
    - `recycle_customer()`：回收至公海池（`assigned_sale_id = None`、`recycled_at = now`）
    - `list_customer_pool()`：公海池查询（`assigned_sale_id IS NULL`）
    - `claim_customer()`：认领校验（未被认领）、状态变更
  - **Commit**: `feat(customers): extract CustomerService with business logic`

- [ ] **精简 customers 路由层**
  - 修改 `api/customers.py`：所有路由函数改为调用 `CustomerService` 方法
  - **Commit**: `refactor(customers): slim down route handlers to call CustomerService`

#### EventService

- [ ] **创建 EventService**
  - 创建 `app/services/event_service.py`
  - 抽取以下业务逻辑到 Service 方法：
    - `list_events()`：查询构建（month/date range/status/planner/venue 筛选）+ 分页
    - `get_event_detail()`：活动详情 + 资源列表 + 排班列表
    - `create_event()`：日期解析（`event_date` alias）、冲突检测、活动创建
    - `update_event()`：变更冲突检测（仅 date/venue 变更时）、字段更新
    - `query_staff_schedule()`：排班查询
    - `check_conflicts()`：冲突检测（对外接口）
    - `detect_conflicts()`：场地冲突查询 + 人员冲突查询（内部方法，从 `_detect_conflicts` 迁移）
    - `add_resource()` / `remove_resource()`：资源管理
  - **Commit**: `feat(events): extract EventService with business logic`

- [ ] **精简 events 路由层**
  - 修改 `api/events.py`：所有路由函数改为调用 `EventService` 方法
  - 移除 `_detect_conflicts` 函数（移入 Service）
  - **Commit**: `refactor(events): slim down route handlers to call EventService`

#### SupplierService

- [ ] **创建 SupplierService**
  - 创建 `app/services/supplier_service.py`
  - 抽取以下业务逻辑到 Service 方法：
    - `list_suppliers()`：查询构建（type/cooperation_status/keyword/rating 筛选）+ 分页
    - `get_supplier_detail()`：供应商详情 + 服务列表 + 最近 5 条评价
    - `create_supplier()` / `update_supplier()`：供应商 CRUD
    - `add_service()` / `update_service()` / `list_services()`：服务项目管理
    - `add_evaluation()`：评分范围校验（1-5）、评价创建、评分平均值重算
    - `list_evaluations()`：评价分页查询
    - `recalculate_rating()`：评分平均值重算（内部方法，从路由内联逻辑迁移）
  - **Commit**: `feat(suppliers): extract SupplierService with business logic`

- [ ] **精简 suppliers 路由层**
  - 修改 `api/suppliers.py`：所有路由函数改为调用 `SupplierService` 方法
  - **Commit**: `refactor(suppliers): slim down route handlers to call SupplierService`

#### UserService

- [ ] **创建 UserService**
  - 创建 `app/services/user_service.py`
  - 抽取以下业务逻辑到 Service 方法：
    - `list_users()`：查询构建（team/status/keyword 筛选）+ 分页
    - `create_user()`：用户名唯一性校验、角色存在性校验、密码哈希、用户创建
    - `update_user()`：角色存在性校验、密码重置哈希、字段更新
    - `list_roles()`：角色列表
    - `update_role()`：权限格式处理（JSON 序列化）
    - `list_operation_logs()`：日志查询 + 用户名关联查询 + 分页
  - **Commit**: `feat(users): extract UserService with business logic`

- [ ] **精简 users 路由层**
  - 修改 `api/users.py`：所有路由函数改为调用 `UserService` 方法
  - 移除 `_MODULE_KEY_MAP`（移入 Service 或独立的 `utils/permissions.py`）
  - **Commit**: `refactor(users): slim down route handlers to call UserService`

---

## 5. 风险与回退

### 5.1 重构风险点

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **行为变更**：重构过程中可能无意中改变业务行为 | 高 | 每个模块重构后立即运行现有测试（如 Playwright E2E），确认所有 API 行为不变 |
| **事务边界变化**：Service 层和事件处理器的 commit/flush 时点可能与原路由不一致 | 高 | 保持 Service 方法与原路由相同的事务边界，不引入新的事务管理策略 |
| **事件处理器异常**：审批事件处理器失败可能导致审批已记录但订单未变更 | 中 | 事件处理器在发布者事务内同步执行，异常时整体回滚 |
| **循环导入**：events/handlers.py 导入 services，services 可能导入 events | 中 | 使用延迟导入（在函数内部 import）打破循环依赖 |
| **性能回归**：Service 方法可能引入额外的数据库查询 | 低 | 保持与原路由相同的查询逻辑，不增加额外查询 |
| **序列化 Helper 归属**：`_xxx_to_dict` 函数留在路由层还是移入 Service | 低 | 本轮保留在路由层，避免过度重构 |

### 5.2 回退策略

1. **逐模块回退**：每个模块的重构是独立的 commit，可单独 `git revert` 回退到重构前状态
2. **API 兼容性**：重构不改变任何 API 接口（路径、参数、响应格式），前端无需任何修改
3. **数据库不变**：不涉及任何数据库 Schema 变更
4. **渐进式重构**：按依赖顺序逐个模块重构，每个模块重构完成后验证通过再进行下一个

### 5.3 验证策略

每个模块重构完成后需验证：
1. **启动验证**：应用能正常启动，无 import 错误
2. **API 行为验证**：通过 E2E 测试或手动测试确认所有 API 返回值不变
3. **审批流程验证**：特别关注审批通过后的订单取消/退款是否正常工作
4. **事件总线验证**：确认事件处理器被正确调用

---

## 6. 不做的事

以下内容**明确排除**在本次重构范围之外：

1. **数据库 Schema 变更**：不修改任何表结构、索引、外键
2. **API 接口变更**：不改变任何 API 路径、请求参数、响应格式
3. **前端代码修改**：前端无需任何改动
4. **Repository 模式引入**：Service 直接使用 SQLAlchemy Session，不抽象 Repository 层
5. **异步消息队列**：不引入 RabbitMQ/Kafka 等外部 MQ，使用进程内同步事件
6. **Dashboard 模块重构**：Dashboard 为只读聚合模块，独立性强，暂不重构
7. **Auth 模块重构**：认证逻辑简单（登录/登出/Token 刷新），不需要抽取 Service
8. **Venues 模块重构**：场地模块为简单 CRUD，暂不抽取 Service
9. **单元测试编写**：本次聚焦架构重构，测试由后续迭代补充
10. **序列化函数迁移**：`_xxx_to_dict` 等 Helper 函数保留在路由层，不迁移到 Service 或独立的 Serializer
11. **操作日志改造**：`log_operation` 仍在路由层调用，不迁移到 Service 内部
12. **N+1 查询优化**：`_event_to_dict` 中的额外查询等问题不在此轮解决
13. **CQRS / 读写分离**：不引入 Command/Query 分离模式
14. **依赖注入框架**：不引入 `dependency-injector` 等框架，Service 在路由函数内手动创建
