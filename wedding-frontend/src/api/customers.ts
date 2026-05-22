import request from './index'

export interface Customer {
  id: number
  name: string
  phone: string
  gender?: string
  wedding_date?: string
  budget?: number
  status: string
  source?: string
  assigned_user?: { id: number; name: string }
  follow_ups?: FollowUp[]
  created_at: string
  updated_at: string
}

export interface FollowUp {
  id: number
  content: string
  type: string
  next_follow_at?: string
  created_at: string
}

export interface CustomerListParams {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  source?: string
  assigned_user_id?: number
}

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export function getCustomers(params?: CustomerListParams): Promise<PaginatedResult<Customer>> {
  return request.get('/customers', { params })
}

export function getCustomer(id: number): Promise<Customer> {
  return request.get(`/customers/${id}`)
}

export function createCustomer(data: Partial<Customer>): Promise<Customer> {
  return request.post('/customers', data)
}

export function updateCustomer(id: number, data: Partial<Customer>): Promise<Customer> {
  return request.put(`/customers/${id}`, data)
}

export function addFollowUp(customerId: number, data: Partial<FollowUp>): Promise<FollowUp> {
  return request.post(`/customers/${customerId}/follow-ups`, data)
}

export function transferCustomer(customerId: number, targetSaleId: number): Promise<void> {
  return request.post(`/customers/${customerId}/transfer`, { target_sale_id: targetSaleId })
}

export function recycleCustomer(customerId: number): Promise<void> {
  return request.post(`/customers/${customerId}/recycle`)
}

export function getCustomerPool(params?: CustomerListParams): Promise<PaginatedResult<Customer>> {
  return request.get('/customer-pool', { params })
}

export function claimCustomer(customerId: number): Promise<void> {
  return request.post(`/customer-pool/${customerId}/claim`)
}
