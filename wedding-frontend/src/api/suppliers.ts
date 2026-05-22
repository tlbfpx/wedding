import request from './index'

export interface Supplier {
  id: number
  name: string
  contact: string
  phone: string
  type: string
  address?: string
  cooperation_status: string
  note?: string
  services?: SupplierService[]
  created_at: string
  updated_at: string
}

export interface SupplierService {
  id: number
  service_name: string
  category: string
  unit_price: number
  description?: string
}

export interface SupplierEvaluation {
  id: number
  supplier_id: number
  order_id: number
  rating: number
  content?: string
  evaluator?: { id: number; name: string }
  created_at: string
}

export interface SupplierListParams {
  page?: number
  page_size?: number
  keyword?: string
  type?: string
  cooperation_status?: string
}

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export function getSuppliers(params?: SupplierListParams): Promise<PaginatedResult<Supplier>> {
  return request.get('/suppliers', { params })
}

export function getSupplier(id: number): Promise<Supplier> {
  return request.get(`/suppliers/${id}`)
}

export function createSupplier(data: Partial<Supplier>): Promise<Supplier> {
  return request.post('/suppliers', data)
}

export function updateSupplier(id: number, data: Partial<Supplier>): Promise<Supplier> {
  return request.put(`/suppliers/${id}`, data)
}

export function getSupplierServices(supplierId: number): Promise<SupplierService[]> {
  return request.get(`/suppliers/${supplierId}/services`)
}

export function addSupplierService(supplierId: number, data: Partial<SupplierService>): Promise<SupplierService> {
  return request.post(`/suppliers/${supplierId}/services`, data)
}

export function updateSupplierService(
  supplierId: number,
  serviceId: number,
  data: Partial<SupplierService>,
): Promise<SupplierService> {
  return request.put(`/suppliers/${supplierId}/services/${serviceId}`, data)
}

export function addSupplierEvaluation(
  supplierId: number,
  data: Partial<SupplierEvaluation>,
): Promise<SupplierEvaluation> {
  return request.post(`/suppliers/${supplierId}/evaluations`, data)
}

export function getSupplierEvaluations(
  supplierId: number,
  params?: { page?: number; page_size?: number },
): Promise<PaginatedResult<SupplierEvaluation>> {
  return request.get(`/suppliers/${supplierId}/evaluations`, { params })
}
