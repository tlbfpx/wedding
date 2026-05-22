import request from './index'

export function exportReport(params: {
  report_type: string
  date_start?: string
  date_end?: string
  status?: string
  sale_id?: number
}): Promise<Blob> {
  return request.get('/reports/export', { params, responseType: 'blob' })
}
