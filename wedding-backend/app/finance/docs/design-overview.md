# 财务管理模块 - 设计概览

> 模块路径: `app/finance`
> 版本: v1.0
> 创建日期: 2026-05-29

---

## 1. 模块职责

财务管理模块负责系统内所有财务相关的业务逻辑，包括：

1. **应收账款管理** — 自动跟踪订单应收，支持逾期预警
2. **收款登记与核销** — 记录客户收款，自动核销应收
3. **退款管理** — 处理退款申请、审批、执行流程
4. **收支明细记录** — 统一记录所有收入和支出
5. **开票管理** — 管理发票申请、开具、作废流程
6. **财务对账** — 生成对账报表，支持数据核对

### 边界界定

**属于本模块:**
- 应收账款的生成、状态跟踪、逾期计算
- 收款记录的增删改查
- 退款的申请、审批、执行
- 收支明细的记录和统计
- 开票申请、状态管理、PDF 上传
- 对账报表生成

**不属于本模块:**
- 订单的创建、修改（由 Order 模块负责）
- 审批流程的通用逻辑（由 Approval 模块负责）
- 供应商的创建、管理（由 Supplier 模块负责）
- 文件上传的通用处理（由通用工具负责）

---

## 2. 领域模型

### 2.1 实体定义

#### Receivable（应收账款）

**职责:** 跟踪订单的应收状态和到期日

**属性:**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| order_id | int | 关联订单 |
| total_amount | Decimal | 应收总额 |
| received_amount | Decimal | 已收金额 |
| status | ReceivableStatus | 应收状态 |
| due_date | date | 应收到期日 |
| overdue_days | int | 逾期天数 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

**状态机 (ReceivableStatus):**
```
                    [收款金额 > 0]
    unpaid ──────────────────────────────> partial
         │                                       │
         │ [收款全额]                            │ [收款全额]
         └───────────────────────────────────────┴───> paid

         [超过到期日且未全额收款]
         │
         v
      overdue
```

**业务规则:**
- 订单创建时自动生成应收记录
- 签约时计算到期日（默认签约后 30 天）
- 收款后自动更新 `received_amount` 和 `status`
- 每日定时任务检查并更新逾期状态

---

#### FinancePayment（收款记录）

**职责:** 记录客户付款，扩展原有 Payment 模型

**属性:**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| order_id | int | 关联订单 |
| amount | Decimal | 收款金额 |
| method | PaymentMethod | 付款方式 |
| paid_at | datetime | 收款日期 |
| note | str | 备注 |
| created_by | int | 创建人 |
| created_at | datetime | 创建时间 |

**与现有 Payment 的关系:**
- 现有 `Payment` 表保留，向后兼容
- `FinancePayment` 增加 `created_by` 字段
- 收款时同时写入两张表（数据迁移期间）
- 迁移完成后逐步废弃 Payment 表

---

#### Refund（退款记录）

**职责:** 管理退款申请、审批、执行流程

**属性:**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| order_id | int | 关联订单 |
| amount | Decimal | 退款金额 |
| reason | str | 退款原因 |
| status | RefundStatus | 退款状态 |
| approval_id | int | 关联审批 |
| approved_by | int | 审批人 |
| approved_at | datetime | 审批时间 |
| refunded_at | datetime | 实际退款时间 |
| note | str | 备注 |
| created_at | datetime | 创建时间 |
| created_by | int | 申请人 |

**状态机 (RefundStatus):**
```
    pending_approval ────> approved ────> refunded
                              │
                              v
                          rejected
```

**业务规则:**
- 退款金额 <= 订单已付金额
- 创建时自动生成 Approval 记录
- 审批通过后扣减订单 `paid_amount`
- 实际退款后标记为 `refunded`

---

#### Transaction（收支明细）

**职责:** 统一记录所有收入和支出

**属性:**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| type | TransactionType | 收支类型（income/expense） |
| category | ExpenseCategory | 支出分类 |
| amount | Decimal | 金额 |
| order_id | int | 关联订单（可选） |
| payment_id | int | 关联收款（收入时） |
| refund_id | int | 关联退款（支出时） |
| supplier_id | int | 关联供应商（可选） |
| date | date | 业务日期 |
| method | str | 付款方式（收入时） |
| note | str | 备注 |
| created_at | datetime | 创建时间 |

**收支类型:**
- `income` — 收入（客户付款）
- `expense` — 支出（供应商付款、其他支出、退款）

**支出分类 (ExpenseCategory):**
- `supplier_payment` — 供应商付款
- `labor` — 人工费用
- `venue` — 场地费用
- `material` — 物料费用
- `other` — 其他
- `refund` — 退款

**业务规则:**
- 收入记录自动生成，不可手动创建
- 支出记录可手动创建和修改
- 删除需管理员权限

---

#### Invoice（开票记录）

**职责:** 管理发票申请、开具、作废流程

**属性:**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| order_id | int | 关联订单 |
| invoice_type | InvoiceType | 发票类型 |
| amount | Decimal | 开票金额 |
| title | str | 发票抬头 |
| tax_no | str | 税号 |
| status | InvoiceStatus | 开票状态 |
| invoice_no | str | 发票号码 |
| pdf_url | str | 发票 PDF 路径 |
| issued_at | datetime | 开票日期 |
| voided_at | datetime | 作废日期 |
| voided_by | int | 作废人 |
| note | str | 备注 |
| created_at | datetime | 创建时间 |
| created_by | int | 申请人 |
| approval_id | int | 关联审批（可选） |

**状态机 (InvoiceStatus):**
```
    pending ────> processing ────> issued
                    │               │
                    └───────────────┘
                                    │
                                    v
                                 voided
```

**业务规则:**
- 开票金额 <= 订单总额
- 超过阈值（默认 50000 元）需审批
- 发票号码唯一性校验
- 已开票记录不可修改金额

---

#### Reconciliation（对账记录）

**职责:** 存储对账快照，支持历史查询

**属性:**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键 |
| period | str | 对账周期（YYYY-MM 或 YYYY-QQ） |
| snapshot | JSON | 对账快照 |
| notes | str | 备注 |
| confirmed_by | int | 确认人 |
| confirmed_at | datetime | 确认时间 |
| created_at | datetime | 创建时间 |

**业务规则:**
- 对账快照独立存储，不受后续数据变更影响
- 仅管理员可确认对账
- 支持按月或按季度对账

---

### 2.2 实体关系图

```
┌─────────────┐
│    Order    │
│   (外部模块) │
└──────┬──────┘
       │ 1
       │
       ├──────────────────────┐
       │                      │
       │ N                    │ N
       ▼                      ▼
┌──────────────┐      ┌──────────────┐
│  Receivable  │      │FinancePayment│
│              │      │              │
└──────────────┘      └──────┬───────┘
                              │ 1
                              │
                              │ 1
                              ▼
                     ┌──────────────┐
                     │ Transaction  │
                     │  (income)    │
                     └──────┬───────┘
                            │
┌──────────────┐             │
│    Refund    │◄────────────┘ (退款生成支出)
│              │
└──────┬───────┘
       │ 1
       │
       │ 1
       ▼
┌──────────────┐
│  Approval   │
│  (外部模块)  │
└──────────────┘

┌──────────────┐      ┌──────────────┐
│   Invoice    │      │Reconciliation│
└──────────────┘      └───────────────┘
```

---

## 3. 核心业务流程

### 3.1 应收生成流程

```python
# 事件驱动: ORDER_CREATED → create_receivable

async def create_receivable(order_id: int, total_amount: Decimal, due_days: int = 30):
    # 1. 检查订单是否已存在应收
    existing = await receivable_repo.get_by_order(order_id)
    if existing:
        raise AppException(400, "RECEIVABLE_EXISTS", "订单已存在应收记录")

    # 2. 创建应收记录
    receivable = Receivable(
        order_id=order_id,
        total_amount=total_amount,
        received_amount=Decimal("0"),
        status=ReceivableStatus.unpaid,
        due_date=None,  # 签约时设置
    )
    await receivable_repo.add(receivable)

    # 3. 发布事件
    await event_bus.publish(DomainEvent(
        event_type="RECEIVABLE_CREATED",
        payload={
            "receivable_id": receivable.id,
            "order_id": order_id,
            "total_amount": str(total_amount),
        }
    ))

    return receivable
```

---

### 3.2 收款核销流程

```python
async def record_payment(data: PaymentCreate, user_id: int):
    # 1. 获取订单和应收
    order = await order_repo.get(data.order_id)
    if not order:
        raise AppException(404, "ORDER_NOT_FOUND", "订单不存在")

    receivable = await receivable_repo.get_by_order(data.order_id)
    if not receivable:
        raise AppException(404, "RECEIVABLE_NOT_FOUND", "应收记录不存在")

    # 2. 校验金额
    new_received = receivable.received_amount + Decimal(str(data.amount))
    if new_received > receivable.total_amount:
        raise AppException(400, "PAYMENT_EXCEEDS_TOTAL", "收款金额超过剩余应收")

    # 3. 创建收款记录（事务保护）
    payment = FinancePayment(
        order_id=data.order_id,
        amount=data.amount,
        method=data.method,
        paid_at=data.paid_at or datetime.utcnow(),
        note=data.note,
        created_by=user_id,
    )

    # 4. 更新应收
    receivable.received_amount = new_received
    await _update_receivable_status(receivable)

    # 5. 创建收入明细
    transaction = Transaction(
        type=TransactionType.income,
        amount=data.amount,
        order_id=data.order_id,
        payment_id=payment.id,
        date=data.paid_at.date() if data.paid_at else date.today(),
        method=data.method.value,
    )

    # 6. 同时写入 Payment 表（兼容期）
    legacy_payment = Payment(
        order_id=data.order_id,
        amount=data.amount,
        method=data.method,
        status=PaymentStatus.confirmed,
        paid_at=payment.paid_at,
        note=data.note,
    )

    await db.commit()
    await db.refresh(payment)

    # 7. 发布事件
    await event_bus.publish(DomainEvent(
        event_type="PAYMENT_RECORDED",
        payload={
            "payment_id": payment.id,
            "order_id": data.order_id,
            "amount": str(data.amount),
            "method": data.method.value,
        }
    ))

    return payment
```

---

### 3.3 退款流程

```python
async def request_refund(order_id: int, amount: Decimal, reason: str, user_id: int):
    # 1. 校验金额
    order = await order_repo.get(order_id)
    if Decimal(str(amount)) > Decimal(str(order.paid_amount)):
        raise AppException(400, "REFUND_EXCEEDS_PAID", "退款金额超过订单已付金额")

    # 2. 创建退款记录
    refund = Refund(
        order_id=order_id,
        amount=amount,
        reason=reason,
        status=RefundStatus.pending_approval,
        created_by=user_id,
    )
    await db.add(refund)
    await db.flush()

    # 3. 创建审批记录
    approval = Approval(
        type=ApprovalType.refund,
        target_id=refund.id,
        applicant_id=user_id,
        reason=reason,
        status=ApprovalStatus.pending,
    )
    await db.add(approval)
    await db.flush()

    refund.approval_id = approval.id

    await db.commit()
    await db.refresh(refund)

    # 4. 发布事件
    await event_bus.publish(DomainEvent(
        event_type="REFUND_REQUESTED",
        payload={
            "refund_id": refund.id,
            "order_id": order_id,
            "amount": str(amount),
            "reason": reason,
            "approval_id": approval.id,
        }
    ))

    return refund


# 审批通过时的处理（事件驱动）
async def on_refund_approved(refund_id: int):
    refund = await refund_repo.get(refund_id)
    if not refund or refund.status != RefundStatus.pending_approval:
        return

    # 1. 更新退款状态
    refund.status = RefundStatus.approved
    refund.approved_at = datetime.utcnow()

    # 2. 扣减订单已付金额
    order = await order_repo.get(refund.order_id)
    order.paid_amount = float(Decimal(str(order.paid_amount)) - Decimal(str(refund.amount)))

    # 3. 重新计算应收
    receivable = await receivable_repo.get_by_order(refund.order_id)
    if receivable:
        receivable.received_amount = Decimal(str(order.paid_amount))
        await _update_receivable_status(receivable)

    await db.commit()

    # 4. 发布事件
    await event_bus.publish(DomainEvent(
        event_type="REFUND_APPROVED",
        payload={
            "refund_id": refund.id,
            "order_id": refund.order_id,
            "amount": str(refund.amount),
        }
    ))


# 实际退款
async def confirm_refund(refund_id: int):
    refund = await refund_repo.get(refund_id)
    if refund.status != RefundStatus.approved:
        raise AppException(400, "INVALID_STATUS", "退款状态不允许此操作")

    # 1. 更新状态
    refund.status = RefundStatus.refunded
    refund.refunded_at = datetime.utcnow()

    # 2. 创建退款支出明细
    transaction = Transaction(
        type=TransactionType.expense,
        category=ExpenseCategory.refund,
        amount=refund.amount,
        order_id=refund.order_id,
        refund_id=refund.id,
        date=date.today(),
        note=f"退款: {refund.reason}",
    )
    await db.add(transaction)

    await db.commit()
    return refund
```

---

### 3.4 开票流程

```python
async def request_invoice(
    order_id: int,
    invoice_type: InvoiceType,
    amount: Decimal,
    title: str,
    tax_no: str,
    user_id: int
):
    # 1. 校验金额
    order = await order_repo.get(order_id)
    if Decimal(str(amount)) > Decimal(str(order.total_amount)):
        raise AppException(400, "INVOICE_AMOUNT_EXCEEDS", "开票金额超过订单总额")

    # 2. 检查是否需要审批（超过阈值）
    approval_id = None
    threshold = Decimal(str(settings.INVOICE_APPROVAL_THRESHOLD))
    if amount > threshold:
        approval = Approval(
            type=ApprovalType.invoice,
            target_id=0,  # 稍后填充
            applicant_id=user_id,
            reason=f"开票申请 {title} ({invoice_type.value})",
            status=ApprovalStatus.pending,
        )
        await db.add(approval)
        await db.flush()
        approval_id = approval.id

    # 3. 创建开票记录
    invoice = Invoice(
        order_id=order_id,
        invoice_type=invoice_type,
        amount=amount,
        title=title,
        tax_no=tax_no,
        status=InvoiceStatus.pending if not approval_id else InvoiceStatus.processing,
        approval_id=approval_id,
        created_by=user_id,
    )
    await db.add(invoice)

    if approval_id:
        approval.target_id = invoice.id

    await db.commit()
    await db.refresh(invoice)

    # 4. 发布事件
    await event_bus.publish(DomainEvent(
        event_type="INVOICE_REQUESTED",
        payload={
            "invoice_id": invoice.id,
            "order_id": order_id,
            "amount": str(amount),
            "invoice_type": invoice_type.value,
        }
    ))

    return invoice
```

---

### 3.5 对账流程

```python
async def generate_reconciliation_report(period: str) -> dict:
    """
    period 格式: "YYYY-MM"（月度）或 "YYYY-QQ"（季度）
    """
    # 1. 解析周期
    if "-Q" in period:
        year, quarter = period.split("-Q")
        # 季度日期范围
    else:
        year, month = period.split("-")
        # 月度日期范围

    # 2. 收入对账
    receivable_result = await db.execute(
        select(Receivable).where(
            Receivable.created_at >= start_date,
            Receivable.created_at < end_date
        )
    )
    receivables = receivable_result.scalars().all()

    receivable_total = sum(r.total_amount for r in receivables)
    received_total = sum(r.received_amount for r in receivables)

    # 差异明细
    income_details = []
    for r in receivables:
        if r.received_amount < r.total_amount:
            income_details.append({
                "order_id": r.order_id,
                "receivable": r.total_amount,
                "received": r.received_amount,
                "difference": r.total_amount - r.received_amount,
            })

    # 3. 支出对账（供应商付款）
    expense_result = await db.execute(
        select(Transaction).where(
            Transaction.type == TransactionType.expense,
            Transaction.category == ExpenseCategory.supplier_payment,
            Transaction.date >= start_date,
            Transaction.date < end_date
        )
    )
    expenses = expense_result.scalars().all()
    expense_total = sum(e.amount for e in expenses)

    # 4. 组装报告
    return {
        "period": period,
        "income_reconciliation": {
            "receivable_total": receivable_total,
            "received_total": received_total,
            "difference": receivable_total - received_total,
            "details": income_details,
        },
        "expense_reconciliation": {
            "paid_total": expense_total,
            "details": [...],
        },
        "generated_at": datetime.utcnow(),
    }


async def confirm_reconciliation(period: str, notes: str, user_id: int):
    # 1. 生成报告
    report = await generate_reconciliation_report(period)

    # 2. 创建对账记录（保存快照）
    reconciliation = Reconciliation(
        period=period,
        snapshot=report,  # JSON 序列化
        notes=notes,
        confirmed_by=user_id,
        confirmed_at=datetime.utcnow(),
    )
    await db.add(reconciliation)
    await db.commit()

    # 3. 发布事件
    await event_bus.publish(DomainEvent(
        event_type="RECONCILIATION_CONFIRMED",
        payload={
            "reconciliation_id": reconciliation.id,
            "period": period,
            "notes": notes,
        }
    ))

    return reconciliation
```

---

## 4. 数据库设计

### 4.1 表结构

#### receivables

```sql
CREATE TABLE receivables (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id),
    total_amount DECIMAL(12, 2) NOT NULL DEFAULT 0,
    received_amount DECIMAL(12, 2) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'unpaid',
    due_date DATE,
    overdue_days INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    CONSTRAINT chk_receivable_amount CHECK (received_amount >= 0)
);

CREATE INDEX ix_receivables_order_id ON receivables(order_id);
CREATE INDEX ix_receivables_status ON receivables(status);
CREATE INDEX ix_receivables_due_date ON receivables(due_date);
```

#### finance_payments

```sql
CREATE TABLE finance_payments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    amount DECIMAL(12, 2) NOT NULL,
    method VARCHAR(20) NOT NULL,
    paid_at TIMESTAMP NOT NULL,
    note VARCHAR(200),
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_payment_amount CHECK (amount > 0)
);

CREATE INDEX ix_finance_payments_order_id ON finance_payments(order_id);
CREATE INDEX ix_finance_payments_paid_at ON finance_payments(paid_at);
CREATE INDEX ix_finance_payments_created_by ON finance_payments(created_by);
```

#### refunds

```sql
CREATE TABLE refunds (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    amount DECIMAL(12, 2) NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending_approval',
    approval_id INTEGER REFERENCES approvals(id),
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMP,
    refunded_at TIMESTAMP,
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    CONSTRAINT chk_refund_amount CHECK (amount > 0)
);

CREATE INDEX ix_refunds_order_id ON refunds(order_id);
CREATE INDEX ix_refunds_status ON refunds(status);
CREATE INDEX ix_refunds_approval_id ON refunds(approval_id);
```

#### transactions

```sql
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    type VARCHAR(20) NOT NULL,
    category VARCHAR(20),
    amount DECIMAL(12, 2) NOT NULL,
    order_id INTEGER REFERENCES orders(id),
    payment_id INTEGER REFERENCES finance_payments(id),
    refund_id INTEGER REFERENCES refunds(id),
    supplier_id INTEGER REFERENCES suppliers(id),
    method VARCHAR(50),
    date DATE NOT NULL,
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_transaction_amount CHECK (amount > 0)
);

CREATE INDEX ix_transactions_type ON transactions(type);
CREATE INDEX ix_transactions_date ON transactions(date);
CREATE INDEX ix_transactions_order_id ON transactions(order_id);
CREATE INDEX ix_transactions_supplier_id ON transactions(supplier_id);
CREATE INDEX ix_transactions_payment_id ON transactions(payment_id);
CREATE INDEX ix_transactions_refund_id ON transactions(refund_id);
```

#### invoices

```sql
CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    invoice_type VARCHAR(20) NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    title VARCHAR(200) NOT NULL,
    tax_no VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    invoice_no VARCHAR(50) UNIQUE,
    pdf_url VARCHAR(500),
    issued_at TIMESTAMP,
    voided_at TIMESTAMP,
    voided_by INTEGER REFERENCES users(id),
    note TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    approval_id INTEGER REFERENCES approvals(id),
    CONSTRAINT chk_invoice_amount CHECK (amount > 0)
);

CREATE INDEX ix_invoices_order_id ON invoices(order_id);
CREATE INDEX ix_invoices_status ON invoices(status);
CREATE INDEX ix_invoices_invoice_no ON invoices(invoice_no);
```

#### reconciliations

```sql
CREATE TABLE reconciliations (
    id SERIAL PRIMARY KEY,
    period VARCHAR(20) NOT NULL UNIQUE,
    snapshot JSONB NOT NULL,
    notes TEXT,
    confirmed_by INTEGER NOT NULL REFERENCES users(id),
    confirmed_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_reconciliations_period ON reconciliations(period);
```

---

### 4.2 索引策略

| 表 | 索引 | 用途 |
|------|------|------|
| receivables | order_id | 唯一约束，按订单查询 |
| receivables | status | 按状态筛选 |
| receivables | due_date | 逾期检查 |
| finance_payments | order_id | 按订单查询收款 |
| finance_payments | paid_at | 按日期范围查询 |
| finance_payments | created_by | 按创建人查询 |
| transactions | type | 按收支类型筛选 |
| transactions | date | 按日期范围查询 |
| transactions | order_id | 关联订单 |
| transactions | supplier_id | 关联供应商 |
| invoices | order_id | 按订单查询 |
| invoices | status | 按状态筛选 |
| invoices | invoice_no | 发票号码唯一性 |

---

## 5. 与其他模块的交互

### 5.1 依赖关系

```
┌─────────────────────────────────────────────────────────────────┐
│                        Finance Module                          │
├─────────────────────────────────────────────────────────────────┤
│  Depends On:                                                    │
│  - Order (订单模块) — 读取订单信息，接收订单事件                │
│  - Approval (审批模块) — 创建审批记录，接收审批事件             │
│  - Supplier (供应商模块) — 读取供应商信息                       │
│  - User (用户模块) — 读取用户信息                               │
│  - Notification (通知模块) — 发送财务通知                      │
│                                                                 │
│  Used By:                                                       │
│  - Dashboard (工作台) — 获取财务汇总                            │
│  - Report (报表模块) — 获取收支明细                            │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 事件订阅

| 事件 | 来源 | 处理器 | 动作 |
|------|------|--------|------|
| ORDER_CREATED | Order | on_order_created | 创建应收记录 |
| ORDER_STATUS_CHANGED | Order | on_order_status_changed | 签约时设置到期日 |
| ORDER_CANCELLED | Order | on_order_cancelled | 关闭关联应收、退款、开票 |
| APPROVAL_APPROVED | Approval | on_approval_approved | 退款审批通过处理 |
| APPROVAL_REJECTED | Approval | on_approval_rejected | 退款审批驳回处理 |

### 5.3 事件发布

| 事件 | 订阅者 | 用途 |
|------|--------|------|
| RECEIVABLE_OVERDUE | Notification | 逾期提醒 |
| PAYMENT_RECORDED | Notification | 收款通知 |
| REFUND_APPROVED | Order | 更新订单金额 |
| INVOICE_ISSUED | Notification | 开票完成通知 |

---

## 6. 扩展点

### 6.1 新增付款方式

在 `PaymentMethod` 枚举中添加新值，无需修改核心逻辑。

### 6.2 新增支出分类

在 `ExpenseCategory` 枚举中添加新值，更新统计逻辑。

### 6.3 对账周期扩展

当前支持月度、季度，可扩展为年度或自定义周期。

### 6.4 发票审批阈值

通过配置文件 `INVOICE_APPROVAL_THRESHOLD` 控制，可根据需要调整。

---

## 7. 性能考虑

### 7.1 查询优化

- 应收列表使用索引 (status, due_date)
- 收支明细按日期范围查询，使用索引 (date)
- 对账报表生成涉及聚合计算，考虑缓存

### 7.2 定时任务

- 逾期检查：每日凌晨执行
- 对账提醒：每月初执行

### 7.3 数据归档

建议对超过 2 年的收支明细进行归档，保持主表性能。

---

## 8. 安全考虑

### 8.1 数据权限

- 普通用户只能查看自己关联的数据
- 财务操作记录操作日志
- 敏感数据（客户抬头、税号）脱敏展示

### 8.2 操作审计

所有财务操作（收款、退款、开票）记录操作日志，包括：
- 操作人
- 操作时间
- 操作类型
- 关联订单/金额

---

## 9. 测试策略

### 9.1 单元测试

- 每个实体的状态机转换
- 金额计算逻辑
- 业务规则校验

### 9.2 集成测试

- 事件驱动流程（订单创建 → 应收生成）
- 收款核销流程
- 退款审批流程

### 9.3 性能测试

- 1000+ 应收记录查询
- 对账报表生成
