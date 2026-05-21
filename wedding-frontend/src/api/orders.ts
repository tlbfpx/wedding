import request from './index'

export interface OrderItem {
  id?: number
  type: string
  name: string
  quantity: number
  unit_price: number
  amount: number
  supplier_id?: number
  supplier?: { id: number; name: string }
  remark?: string
}

export interface Order {
  id: number
  order_no: string
  customer_id: number
  customer?: { id: number; name: string; phone: string }
  event_id?: number
  sale_id?: number
  sale?: { id: number; name: string }
  planner_id?: number
  planner?: { id: number; name: string }
  status: string
  total_amount: number
  paid_amount: number
  discount?: number
  remark?: string
  items?: OrderItem[]
  payments?: Payment[]
  contract_url?: string
  contract_name?: string
  created_at: string
  updated_at: string
}

export interface Payment {
  id: number
  amount: number
  method: string
  paid_at?: string
  remark?: string
  created_at: string
}

export interface OrderListParams {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  customer_id?: number
  start_date?: string
  end_date?: string
}

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface Approval {
  id: number
  type: string
  order_id?: number
  order_no?: string
  applicant_id: number
  applicant?: { id: number; name: string }
  reason: string
  status: string
  approver_id?: number
  approver?: { id: number; name: string }
  approver_remark?: string
  created_at: string
  updated_at?: string
}

export interface ApprovalListParams {
  page?: number
  page_size?: number
  status?: string
  type?: string
}

export function getOrders(params?: OrderListParams): Promise<PaginatedResult<Order>> {
  return request.get('/orders', { params })
}

export function getOrder(id: number): Promise<Order> {
  return request.get(`/orders/${id}`)
}

export function createOrder(data: Partial<Order> & { items?: OrderItem[] }): Promise<Order> {
  return request.post('/orders', data)
}

export function updateOrder(id: number, data: Partial<Order>): Promise<Order> {
  return request.put(`/orders/${id}`, data)
}

export function updateOrderStatus(id: number, status: string): Promise<void> {
  return request.put(`/orders/${id}/status`, { status })
}

export function addPayment(orderId: number, data: Partial<Payment>): Promise<Payment> {
  return request.post(`/orders/${orderId}/payments`, data)
}

export function uploadContract(orderId: number, file: File): Promise<void> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post(`/orders/${orderId}/contract`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getQuotePdf(orderId: number): Promise<Blob> {
  return request.get(`/orders/${orderId}/quote-pdf`, {
    responseType: 'blob',
  })
}

export function getApprovals(params?: ApprovalListParams): Promise<PaginatedResult<Approval>> {
  return request.get('/approvals', { params })
}

export function approveApproval(id: number, data: { note?: string }): Promise<void> {
  return request.put(`/approvals/${id}`, { status: 'approved', note: data.note })
}

export function rejectApproval(id: number, data: { note?: string }): Promise<void> {
  return request.put(`/approvals/${id}`, { status: 'rejected', note: data.note })
}

export function createApproval(data: {
  type: string
  order_id?: number
  reason: string
}): Promise<Approval> {
  return request.post('/approvals', data)
}
