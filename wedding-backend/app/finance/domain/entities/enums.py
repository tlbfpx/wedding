"""
财务管理模块枚举定义
"""

import enum


class ReceivableStatus(str, enum.Enum):
    """应收状态"""
    unpaid = "unpaid"          # 未收款
    partial = "partial"        # 部分收款
    paid = "paid"              # 已收款
    overdue = "overdue"        # 已逾期


class RefundStatus(str, enum.Enum):
    """退款状态"""
    pending_approval = "pending_approval"  # 待审批
    approved = "approved"                # 已批准
    rejected = "rejected"                # 已拒绝
    refunded = "refunded"                # 已退款


class TransactionType(str, enum.Enum):
    """收支类型"""
    income = "income"          # 收入
    expense = "expense"        # 支出


class ExpenseCategory(str, enum.Enum):
    """支出分类"""
    supplier_payment = "supplier_payment"  # 供应商付款
    labor = "labor"                      # 人工费用
    venue = "venue"                      # 场地费用
    material = "material"                # 物料费用
    other = "other"                      # 其他
    refund = "refund"                    # 退款


class InvoiceType(str, enum.Enum):
    """发票类型"""
    normal = "normal"          # 增值税普通发票
    special = "special"        # 增值税专用发票


class InvoiceStatus(str, enum.Enum):
    """开票状态"""
    pending = "pending"        # 待开票
    processing = "processing"  # 开票中（待审批）
    issued = "issued"          # 已开票
    voided = "voided"          # 已作废


# 付款方式复用订单模块定义
class PaymentMethod(str, enum.Enum):
    cash = "cash"
    transfer = "transfer"
    wechat = "wechat"
    alipay = "alipay"
    card = "card"

