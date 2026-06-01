import request from './index'

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// --- Enums ---

export type ReceivableStatus = 'unpaid' | 'partial' | 'paid' | 'overdue'
export type RefundStatus = 'pending_approval' | 'approved' | 'rejected' | 'refunded'
export type TransactionType = 'income' | 'expense'
export type ExpenseCategory = 'supplier_payment' | 'labor' | 'venue' | 'material' | 'other' | 'refund'
export type InvoiceType = 'normal' | 'special'
export type InvoiceStatus = 'pending' | 'processing' | 'issued' | 'voided'
export type PaymentMethod = 'cash' | 'transfer' | 'wechat' | 'alipay' | 'card'

// --- Receivable ---

export interface Receivable {
  id: number
  order_id: number
  order_no?: string
  customer_name?: string
  customer_phone?: string
  sale_name?: string
  total_amount: string
  received_amount: string
  remaining_amount: string
  status: ReceivableStatus
  due_date: string | null
  is_overdue: boolean
  overdue_days: number
  payments?: FinancePayment[]
  created_at: string | null
  updated_at: string | null
}

export interface ReceivableListParams {
  page?: number
  page_size?: number
  status?: ReceivableStatus
  sale_id?: number
  date_start?: string
  date_end?: string
  keyword?: string
}

// --- FinancePayment ---

export interface FinancePayment {
  id: number
  order_id: number
  amount: string
  method: PaymentMethod
  paid_at: string | null
  note: string | null
  created_by: number
  created_at: string | null
}

export interface PaymentCreateParams {
  order_id: number
  amount: number
  method: PaymentMethod
  paid_at?: string
  note?: string
}

export interface PaymentUpdateParams {
  amount?: number
  method?: PaymentMethod
  paid_at?: string
  note?: string
}

export interface PaymentListParams {
  page?: number
  page_size?: number
  order_id?: number
  method?: PaymentMethod
  date_start?: string
  date_end?: string
}

// --- Refund ---

export interface Refund {
  id: number
  order_id: number
  amount: string
  reason: string
  status: RefundStatus
  approval_id: number | null
  approved_by: number | null
  approved_at: string | null
  refunded_at: string | null
  note: string | null
  created_by?: number
  created_at: string | null
}

export interface RefundCreateParams {
  order_id: number
  amount: number
  reason: string
  note?: string
}

export interface RefundListParams {
  page?: number
  page_size?: number
  order_id?: number
  status?: RefundStatus
}

// --- Transaction ---

export interface Transaction {
  id: number
  type: TransactionType
  category: ExpenseCategory | null
  amount: string
  order_id: number | null
  supplier_id: number | null
  date: string | null
  method: string | null
  note: string | null
  created_at: string | null
}

export interface ExpenseCreateParams {
  category: ExpenseCategory
  amount: number
  order_id?: number
  supplier_id?: number
  date?: string
  note?: string
}

export interface ExpenseUpdateParams {
  amount?: number
  category?: ExpenseCategory
  note?: string
}

export interface TransactionListParams {
  page?: number
  page_size?: number
  type?: TransactionType
  category?: ExpenseCategory
  order_id?: number
  supplier_id?: number
  date_start?: string
  date_end?: string
}

export interface TransactionSummary {
  income_total: string
  expense_total: string
  net_amount: string
  by_category: Record<string, string>
}

// --- Invoice ---

export interface Invoice {
  id: number
  order_id: number
  invoice_type: InvoiceType
  amount: string
  title: string
  tax_no: string
  status: InvoiceStatus
  invoice_no: string | null
  pdf_url: string | null
  issued_at: string | null
  voided_at: string | null
  voided_by: number | null
  note: string | null
  created_by?: number
  approval_id: number | null
  created_at: string | null
}

export interface InvoiceCreateParams {
  order_id: number
  invoice_type: InvoiceType
  amount: number
  title: string
  tax_no: string
  note?: string
}

export interface InvoiceUpdateParams {
  status?: InvoiceStatus
  invoice_no?: string
  issued_at?: string
}

export interface InvoiceListParams {
  page?: number
  page_size?: number
  order_id?: number
  status?: InvoiceStatus
  invoice_type?: InvoiceType
}

// --- Reconciliation ---

export interface ReconciliationReport {
  [key: string]: unknown
}

export interface ReconciliationConfirmParams {
  period: string
  notes?: string
}

export interface ReconciliationRecord {
  id: number
  period: string
  snapshot: string
  confirmed_by: number
  confirmed_at: string | null
  notes: string | null
  created_at: string | null
}

// --- API Functions: Receivables ---

export function getReceivables(params?: ReceivableListParams): Promise<PaginatedResult<Receivable>> {
  return request.get('/finance/receivables', { params })
}

export function getReceivable(id: number): Promise<Receivable> {
  return request.get(`/finance/receivables/${id}`)
}

export function getOverdueReceivables(params?: { page?: number; page_size?: number }): Promise<PaginatedResult<Receivable>> {
  return request.get('/finance/receivables/overdue', { params })
}

// --- API Functions: Payments ---

export function getPayments(params?: PaymentListParams): Promise<PaginatedResult<FinancePayment>> {
  return request.get('/finance/payments', { params })
}

export function createPayment(data: PaymentCreateParams): Promise<FinancePayment> {
  return request.post('/finance/payments', data)
}

export function updatePayment(id: number, data: PaymentUpdateParams): Promise<FinancePayment> {
  return request.put(`/finance/payments/${id}`, data)
}

export function deletePayment(id: number): Promise<{ message: string }> {
  return request.delete(`/finance/payments/${id}`)
}

// --- API Functions: Refunds ---

export function getRefunds(params?: RefundListParams): Promise<PaginatedResult<Refund>> {
  return request.get('/finance/refunds', { params })
}

export function getRefund(id: number): Promise<Refund> {
  return request.get(`/finance/refunds/${id}`)
}

export function createRefund(data: RefundCreateParams): Promise<Refund> {
  return request.post('/finance/refunds', data)
}

export function updateRefundStatus(id: number, status: RefundStatus): Promise<Refund> {
  return request.put(`/finance/refunds/${id}/status`, { status })
}

// --- API Functions: Transactions ---

export function getTransactions(params?: TransactionListParams): Promise<PaginatedResult<Transaction>> {
  return request.get('/finance/transactions', { params })
}

export function createExpense(data: ExpenseCreateParams): Promise<Transaction> {
  return request.post('/finance/transactions', data)
}

export function updateTransaction(id: number, data: ExpenseUpdateParams): Promise<Transaction> {
  return request.put(`/finance/transactions/${id}`, data)
}

export function getTransactionSummary(start_date: string, end_date: string): Promise<TransactionSummary> {
  return request.get('/finance/transactions/summary', { params: { start_date, end_date } })
}

// --- API Functions: Invoices ---

export function getInvoices(params?: InvoiceListParams): Promise<PaginatedResult<Invoice>> {
  return request.get('/finance/invoices', { params })
}

export function getInvoice(id: number): Promise<Invoice> {
  return request.get(`/finance/invoices/${id}`)
}

export function createInvoice(data: InvoiceCreateParams): Promise<Invoice> {
  return request.post('/finance/invoices', data)
}

export function updateInvoice(id: number, data: InvoiceUpdateParams): Promise<Invoice> {
  return request.put(`/finance/invoices/${id}`, data)
}

export function voidInvoice(id: number): Promise<Invoice> {
  return request.delete(`/finance/invoices/${id}`)
}

export function uploadInvoicePdf(id: number, file: File): Promise<{ id: number; pdf_url: string; uploaded_at: string }> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post(`/finance/invoices/${id}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// --- API Functions: Reconciliations ---

export function getReconciliationReport(period: string): Promise<ReconciliationReport> {
  return request.get('/finance/reconciliations/report', { params: { period } })
}

export function confirmReconciliation(data: ReconciliationConfirmParams): Promise<ReconciliationRecord> {
  return request.post('/finance/reconciliations/confirm', data)
}

export function getReconciliationHistory(params?: { page?: number; page_size?: number }): Promise<PaginatedResult<ReconciliationRecord>> {
  return request.get('/finance/reconciliations/history', { params })
}
