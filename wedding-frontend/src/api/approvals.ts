import request from './index'

export interface Approval {
  id: number
  type: string
  target_id: number
  applicant_id: number
  approver_id?: number
  status: string
  reason: string
  resolved_at?: string
  created_at: string
}

export interface ApprovalListParams {
  page?: number
  page_size?: number
  status?: string
  type?: string
  applicant_id?: number
}

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export function getApprovals(params?: ApprovalListParams): Promise<PaginatedResult<Approval>> {
  return request.get('/approvals', { params })
}

export function createApproval(data: {
  type: string
  target_id: number
  reason: string
}): Promise<Approval> {
  return request.post('/approvals', data)
}

export function decideApproval(
  id: number,
  data: { status: string; note?: string },
): Promise<Approval> {
  return request.put(`/approvals/${id}`, data)
}
