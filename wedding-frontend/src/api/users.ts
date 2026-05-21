import request from './index'

export interface User {
  id: number
  username: string
  name: string
  phone?: string
  team?: string
  role?: string
  status: string
  created_at: string
}

export interface Role {
  id: number
  name: string
  display_name: string
  permissions: string[]
}

export interface OperationLog {
  id: number
  user_id: number
  user_name: string
  action: string
  resource_type: string
  resource_id?: number
  detail?: string
  ip?: string
  created_at: string
}

export interface UserListParams {
  page?: number
  page_size?: number
  keyword?: string
  team?: string
  status?: string
}

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export function getUsers(params?: UserListParams): Promise<PaginatedResult<User>> {
  return request.get('/users', { params })
}

export function createUser(data: Partial<User> & { password: string }): Promise<User> {
  return request.post('/users', data)
}

export function updateUser(id: number, data: Partial<User>): Promise<User> {
  return request.put(`/users/${id}`, data)
}

export function getRoles(): Promise<Role[]> {
  return request.get('/users/roles')
}

export function updateRole(id: number, data: Partial<Role>): Promise<Role> {
  return request.put(`/users/roles/${id}`, data)
}

export function getOperationLogs(params?: {
  page?: number
  page_size?: number
  user_id?: number
  module?: string
  action?: string
  date_start?: string
  date_end?: string
}): Promise<PaginatedResult<OperationLog>> {
  return request.get('/users/operation-logs', { params })
}
