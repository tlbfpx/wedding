"""
财务管理模块领域事件类型定义
"""

# 应收相关事件
RECEIVABLE_CREATED = "finance.receivable_created"
RECEIVABLE_OVERDUE = "finance.receivable_overdue"
RECEIVABLE_STATUS_CHANGED = "finance.receivable_status_changed"

# 收款相关事件
PAYMENT_RECORDED = "finance.payment_recorded"
PAYMENT_MODIFIED = "finance.payment_modified"
PAYMENT_DELETED = "finance.payment_deleted"

# 退款相关事件
REFUND_REQUESTED = "finance.refund_requested"
REFUND_APPROVED = "finance.refund_approved"
REFUND_REJECTED = "finance.refund_rejected"
REFUND_CONFIRMED = "finance.refund_confirmed"

# 开票相关事件
INVOICE_REQUESTED = "finance.invoice_requested"
INVOICE_ISSUED = "finance.invoice_issued"
INVOICE_VOIDED = "finance.invoice_voided"

# 对账相关事件
RECONCILIATION_CONFIRMED = "finance.reconciliation_confirmed"

# 收支明细事件
TRANSACTION_CREATED = "finance.transaction_created"
