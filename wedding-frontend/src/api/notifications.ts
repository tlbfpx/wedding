import request from './index'

export interface Notification {
  id: number
  title: string
  content: string
  type: string
  is_read: boolean
  related_id: number | null
  related_type: string | null
  created_at: string | null
}

export function getNotifications(params?: {
  is_read?: boolean
  type?: string
  page?: number
  page_size?: number
}): Promise<any> {
  return request.get('/notifications', { params })
}

export function getUnreadCount(): Promise<{ count: number }> {
  return request.get('/notifications/unread-count')
}

export function markAsRead(ids: number[]): Promise<any> {
  return request.put('/notifications/read', { ids })
}

export function markAllAsRead(): Promise<any> {
  return request.put('/notifications/read-all')
}
