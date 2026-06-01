# 财务管理模块 - 接口契约

> 模块路径: `app/finance`
> API 前缀: `/api/v1/finance`
> 版本: v1.0

---

## 1. Service 接口（暴露给其他模块）

财务管理模块提供以下服务接口，供其他模块调用：

### 1.1 ReceivableService

```python
class ReceivableService:
    """应收账款服务"""

    async def create_receivable(
        self,
        order_id: int,
        total_amount: Decimal,
        due_days: int = 30
    ) -> Receivable:
        """为订单创建应收记录

        Args:
            order_id: 订单ID
            total_amount: 应收总额
            due_days: 付款期限天数（默认签约后30天）

        Returns:
            Receivable: 应收记录

        Raises:
            AppException: 订单不存在或已存在应收记录
        """

    async def get_receivable_by_order(self, order_id: int) -> Optional[Receivable]:
        """根据订单ID获取应收记录"""

    async def update_receivable_status(self, receivable_id: int) -> None:
        """更新应收状态（根据已收金额自动计算）

        状态规则:
        - received_amount == 0: unpaid
        - 0 < received_amount < total_amount: partial
        - received_amount >= total_amount: paid
        - 当前日期 > due_date 且未全额收款: overdue
        """

    async def check_overdue_receivables(self) -> list[Receivable]:
        """获取逾期应收列表（用于定时任务）"""
```

### 1.2 TransactionService

```python
class TransactionService:
    """收支明细服务"""

    async def create_income_transaction(
        self,
        payment_id: int,
        order_id: int,
        amount: Decimal,
        method: str,
        paid_at: datetime
    ) -> Transaction:
        """创建收入记录（收款时自动生成）

        Args:
            payment_id: 收款记录ID
            order_id: 订单ID
            amount: 金额
            method: 付款方式
            paid_at: 收款日期

        Returns:
            Transaction: 收入记录
        """

    async def create_expense_transaction(
        self,
        category: ExpenseCategory,
        amount: Decimal,
        order_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        date: date = None,
        note: Optional[str] = None,
        created_by: int = None
    ) -> Transaction:
        """创建支出记录（手动登记）"""

    async def create_refund_transaction(
        self,
        refund_id: int,
        order_id: int,
        amount: Decimal,
        refunded_at: datetime
    ) -> Transaction:
        """创建退款支出记录"""
```

### 1.3 FinanceStatsService

```python
class FinanceStatsService:
    """财务统计服务（供工作台、报表使用）"""

    async def get_dashboard_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """获取财务汇总数据

        Returns:
            {
                "total_receivable": Decimal,      # 应收总额
                "total_received": Decimal,        # 实收总额
                "overdue_amount": Decimal,        # 逾期金额
                "pending_refund_count": int,      # 待处理退款数
                "pending_invoice_count": int,     # 待开票数
            }
        """

    async def get_team_summary(
        self,
        team: str,
        start_date: date,
        end_date: date
    ) -> dict:
        """获取团队财务汇总"""
```

---

## 2. Controller 接口（HTTP API）

### 2.1 应收账款 API

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| GET | `/receivables` | 应收账款列表 | `finance:read` |
| GET | `/receivables/:id` | 应收详情 | `finance:read` |
| GET | `/receivables/overdue` | 逾期应收列表 | `finance:read` |

#### GET /receivables

**Query Parameters:**
```python
{
    "status": Optional[ReceivableStatus],  # unpaid/partial/paid/overdue
    "sale_id": Optional[int],
    "date_start": Optional[date],
    "date_end": Optional[date],
    "keyword": Optional[str],  # 搜索订单号
    "page": int = 1,
    "page_size": int = 20
}
```

**Response:**
```python
{
    "items": [
        {
            "id": int,
            "order_id": int,
            "order_no": str,
            "customer_name": str,
            "sale_name": str,
            "total_amount": Decimal,      # 应收总额
            "received_amount": Decimal,    # 已收金额
            "remaining_amount": Decimal,   # 剩余应收
            "status": ReceivableStatus,
            "due_date": date,
            "is_overdue": bool,
            "created_at": datetime
        }
    ],
    "total": int,
    "page": int,
    "page_size": int,
    "total_pages": int
}
```

#### GET /receivables/:id

**Response:**
```python
{
    "id": int,
    "order_id": int,
    "order_no": str,
    "customer_name": str,
    "customer_phone": str,
    "sale_name": str,
    "total_amount": Decimal,
    "received_amount": Decimal,
    "remaining_amount": Decimal,
    "status": ReceivableStatus,
    "due_date": date,
    "is_overdue": bool,
    "created_at": datetime,
    "updated_at": datetime,
    "payments": [                    # 关联收款记录
        {
            "id": int,
            "amount": Decimal,
            "method": PaymentMethod,
            "paid_at": datetime,
            "created_by_name": str
        }
    ]
}
```

---

### 2.2 收款登记 API

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| POST | `/payments` | 登记收款 | `finance:write` |
| GET | `/payments` | 收款记录列表 | `finance:read` |
| PUT | `/payments/:id` | 修改收款记录 | `finance:write` + 审核 |
| DELETE | `/payments/:id` | 删除收款记录 | `finance:write` + 审核 |

#### POST /payments

**Request Body:**
```python
{
    "order_id": int,
    "amount": Decimal,
    "method": PaymentMethod,  # cash/transfer/wechat/alipay/card
    "paid_at": datetime,
    "note": Optional[str]
}
```

**Response:**
```python
{
    "id": int,
    "order_id": int,
    "order_no": str,
    "amount": Decimal,
    "method": PaymentMethod,
    "paid_at": datetime,
    "note": Optional[str],
    "created_by": int,
    "created_at": datetime
}
```

**业务规则:**
- 收款金额 + 已收金额 <= 订单总额
- 收款金额必须 > 0
- 收款后自动更新应收状态

#### GET /payments

**Query Parameters:**
```python
{
    "order_id": Optional[int],
    "method": Optional[PaymentMethod],
    "date_start": Optional[date],
    "date_end": Optional[date],
    "page": int = 1,
    "page_size": int = 20
}
```

---

### 2.3 退款 API

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| POST | `/refunds` | 申请退款 | `finance:write` |
| GET | `/refunds` | 退款记录列表 | `finance:read` |
| GET | `/refunds/:id` | 退款详情 | `finance:read` |
| PUT | `/refunds/:id/status` | 更新退款状态（标记已退款） | `finance:write` |

#### POST /refunds

**Request Body:**
```python
{
    "order_id": int,
    "amount": Decimal,
    "reason": str,
    "note": Optional[str]
}
```

**Response:**
```python
{
    "id": int,
    "order_id": int,
    "order_no": str,
    "amount": Decimal,
    "reason": str,
    "status": RefundStatus,  # pending_approval
    "approval_id": int,
    "created_at": datetime
}
```

**业务规则:**
- 退款金额 <= 订单已付金额
- 自动创建 Approval 记录（type=refund）
- 审批通过后自动扣减订单已付金额

#### PUT /refunds/:id/status

**Request Body:**
```python
{
    "status": "refunded"
}
```

---

### 2.4 收支明细 API

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| GET | `/transactions` | 收支明细列表 | `finance:read` |
| POST | `/transactions` | 手动登记支出 | `finance:write` |
| PUT | `/transactions/:id` | 修改支出记录 | `finance:write` |
| GET | `/transactions/summary` | 收支汇总统计 | `finance:read` |
| GET | `/transactions/export` | 导出收支明细（Excel） | `finance:export` |

#### GET /transactions

**Query Parameters:**
```python
{
    "type": Optional[TransactionType],      # income/expense
    "category": Optional[ExpenseCategory],  # 支出分类
    "order_id": Optional[int],
    "supplier_id": Optional[int],
    "date_start": Optional[date],
    "date_end": Optional[date],
    "page": int = 1,
    "page_size": int = 20
}
```

**Response:**
```python
{
    "items": [
        {
            "id": int,
            "type": TransactionType,
            "category": Optional[ExpenseCategory],
            "amount": Decimal,
            "order_id": Optional[int],
            "order_no": Optional[str],
            "supplier_id": Optional[int],
            "supplier_name": Optional[str],
            "date": date,
            "note": Optional[str],
            "created_at": datetime
        }
    ],
    "total": int,
    "page": int,
    "page_size": int,
    "total_pages": int
}
```

#### GET /transactions/summary

**Query Parameters:**
```python
{
    "start_date": date,
    "end_date": date
}
```

**Response:**
```python
{
    "income_total": Decimal,
    "expense_total": Decimal,
    "net_amount": Decimal,
    "by_category": {
        "supplier_payment": Decimal,
        "labor": Decimal,
        "venue": Decimal,
        "material": Decimal,
        "other": Decimal
    },
    "refund_total": Decimal
}
```

---

### 2.5 开票 API

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| POST | `/invoices` | 申请开票 | `finance:write` |
| GET | `/invoices` | 开票记录列表 | `finance:read` |
| GET | `/invoices/:id` | 开票详情 | `finance:read` |
| PUT | `/invoices/:id` | 更新开票状态/上传发票 | `finance:write` |
| DELETE | `/invoices/:id` | 作废发票 | `finance:approve` |
| POST | `/invoices/:id/upload` | 上传发票 PDF | `finance:write` |

#### POST /invoices

**Request Body:**
```python
{
    "order_id": int,
    "invoice_type": InvoiceType,  # normal/special
    "amount": Decimal,
    "title": str,          # 发票抬头
    "tax_no": str,         # 税号
    "note": Optional[str]
}
```

**Response:**
```python
{
    "id": int,
    "order_id": int,
    "order_no": str,
    "invoice_type": InvoiceType,
    "amount": Decimal,
    "title": str,
    "tax_no": str,
    "status": InvoiceStatus,  # pending
    "created_at": datetime
}
```

**业务规则:**
- 开票金额 <= 订单总额
- 超过配置阈值（默认 50000 元）需审批
- 发票号码唯一性校验

#### PUT /invoices/:id

**Request Body:**
```python
{
    "status": InvoiceType,  # processing/issued
    "invoice_no": Optional[str],
    "issued_at": Optional[datetime]
}
```

#### POST /invoices/:id/upload

**Request:**
- Multipart/form-data
- Field: `file` (PDF)

**Response:**
```python
{
    "id": int,
    "pdf_url": str,
    "uploaded_at": datetime
}
```

---

### 2.6 对账 API

| 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|
| GET | `/reconciliation/report` | 生成对账报表 | `finance:read` |
| POST | `/reconciliation/confirm` | 确认对账 | `finance:approve` |
| GET | `/reconciliation/history` | 对账历史记录 | `finance:read` |

#### GET /reconciliation/report

**Query Parameters:**
```python
{
    "period": str,  # 格式: "YYYY-MM"（月度）或 "YYYY-QQ"（季度）
}
```

**Response:**
```python
{
    "period": str,
    "income_reconciliation": {
        "receivable_total": Decimal,
        "received_total": Decimal,
        "difference": Decimal,
        "details": [
            {
                "order_id": int,
                "order_no": str,
                "receivable": Decimal,
                "received": Decimal,
                "difference": Decimal
            }
        ]
    },
    "expense_reconciliation": {
        "payable_total": Decimal,
        "paid_total": Decimal,
        "difference": Decimal,
        "details": [...]
    },
    "generated_at": datetime
}
```

#### POST /reconciliation/confirm

**Request Body:**
```python
{
    "period": str,
    "notes": Optional[str]
}
```

**Response:**
```python
{
    "id": int,
    "period": str,
    "snapshot": dict,  # 对账快照（JSON）
    "confirmed_by": int,
    "confirmed_at": datetime,
    "notes": str
}
```

---

## 3. Events（领域事件）

### 3.1 本模块发布的事件

| 事件名称 | 触发条件 | 负载（Payload） |
|----------|----------|----------------|
| `RECEIVABLE_CREATED` | 应收记录创建 | `{receivable_id, order_id, total_amount, due_date}` |
| `RECEIVABLE_OVERDUE` | 应收逾期 | `{receivable_id, order_id, due_date, overdue_days}` |
| `PAYMENT_RECORDED` | 收款登记 | `{payment_id, order_id, amount, method, paid_at}` |
| `REFUND_REQUESTED` | 退款申请 | `{refund_id, order_id, amount, reason, approval_id}` |
| `REFUND_APPROVED` | 退款审批通过 | `{refund_id, order_id, amount}` |
| `REFUND_REJECTED` | 退款审批驳回 | `{refund_id, order_id, reason}` |
| `INVOICE_REQUESTED` | 开票申请 | `{invoice_id, order_id, amount, invoice_type}` |
| `INVOICE_ISSUED` | 发票开具 | `{invoice_id, order_id, invoice_no, issued_at}` |
| `RECONCILIATION_CONFIRMED` | 对账确认 | `{reconciliation_id, period, notes}` |

### 3.2 本模块订阅的事件

| 事件名称 | 来源模块 | 处理动作 |
|----------|----------|----------|
| `ORDER_CREATED` | Order | 自动创建应收记录（Receivable） |
| `ORDER_STATUS_CHANGED` | Order | 订单签约时计算应收到期日 |
| `ORDER_CANCELLED` | Order | 取消订单时关闭关联应收、退款、开票 |
| `APPROVAL_APPROVED` | Approval | 退款审批通过时更新退款状态、扣减订单金额 |
| `APPROVAL_REJECTED` | Approval | 退款审批驳回时更新退款状态 |

### 3.3 事件处理器注册

```python
# app/finance/interfaces/subscribers/event_handlers.py

async def on_order_created(event: DomainEvent, context: dict = None):
    """订单创建时自动生成应收记录"""
    order_id = event.payload["order_id"]
    total_amount = event.payload["total_amount"]
    service = ReceivableService(context["db"])
    await service.create_receivable(order_id, total_amount)


async def on_order_status_changed(event: DomainEvent, context: dict = None):
    """订单状态变更时更新应收"""
    order_id = event.payload["order_id"]
    new_status = event.payload["new_status"]

    if new_status == "signed":
        # 签约时计算到期日（默认30天后）
        service = ReceivableService(context["db"])
        receivable = await service.get_receivable_by_order(order_id)
        if receivable:
            from datetime import timedelta
            receivable.due_date = date.today() + timedelta(days=30)
            await context["db"].commit()


async def on_approval_approved(event: DomainEvent, context: dict = None):
    """审批通过时处理退款"""
    approval_type = event.payload["approval_type"]
    if approval_type == "refund":
        target_id = event.payload["target_id"]
        service = RefundService(context["db"])
        await service.handle_approval_approved(target_id)


def register_finance_event_handlers():
    from app.events import event_bus
    from app.events.event_types import ORDER_CREATED, ORDER_STATUS_CHANGED, APPROVAL_APPROVED

    event_bus.subscribe(ORDER_CREATED, on_order_created)
    event_bus.subscribe(ORDER_STATUS_CHANGED, on_order_status_changed)
    event_bus.subscribe(APPROVAL_APPROVED, on_approval_approved)
```

---

## 4. 权限定义

### 4.1 权限标识

| 权限 | 说明 |
|------|------|
| `finance:read` | 查看财务数据（应收、收款、收支明细、对账报表） |
| `finance:write` | 财务操作（收款登记、退款申请、开票申请、支出登记） |
| `finance:approve` | 财务审批（退款审批、对账确认、发票作废） |
| `finance:export` | 财务报表导出 |

### 4.2 权限矩阵

| 角色 | read | write | approve | export |
|------|------|-------|---------|--------|
| 管理员 | all | all | all | all |
| 销售主管 | all | own/team | - | - |
| 销售 | own | own | - | - |
| 策划主管 | all | - | - | - |

**注**: `own` 表示仅查看/操作自己关联的订单数据；`team` 表示团队范围内。

---

## 5. 错误码定义

| 错误码 | HTTP状态 | 说明 |
|--------|----------|------|
| `RECEIVABLE_EXISTS` | 400 | 订单已存在应收记录 |
| `PAYMENT_EXCEEDS_TOTAL` | 400 | 收款金额超过订单剩余应收 |
| `REFUND_EXCEEDS_PAID` | 400 | 退款金额超过订单已付金额 |
| `INVOICE_AMOUNT_EXCEEDS` | 400 | 开票金额超过订单总额 |
| `INVOICE_NO_EXISTS` | 400 | 发票号码已存在 |
| `RECEIVABLE_NOT_FOUND` | 404 | 应收记录不存在 |
| `PAYMENT_NOT_FOUND` | 404 | 收款记录不存在 |
| `REFUND_NOT_FOUND` | 404 | 退款记录不存在 |
| `INVOICE_NOT_FOUND` | 404 | 开票记录不存在 |
