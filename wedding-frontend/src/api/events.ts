import request from './index'

export interface Event {
  id: number
  title: string
  customer_id: number
  customer?: { id: number; name: string }
  venue_id?: number
  venue?: { id: number; name: string }
  event_date: string
  start_time: string
  end_time: string
  status: string
  type?: string
  guest_count?: number
  remark?: string
  resources?: EventResource[]
  created_at: string
  updated_at: string
}

export interface EventResource {
  id: number
  resource_type: string
  resource_id: number
  resource_name?: string
  quantity: number
  start_time?: string
  end_time?: string
}

export interface EventListParams {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  start_date?: string
  end_date?: string
  venue_id?: number
}

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface Conflict {
  resource_type: string
  resource_name: string
  event_id: number
  event_title: string
  conflict_start: string
  conflict_end: string
}

export function getEvents(params?: EventListParams): Promise<PaginatedResult<Event>> {
  return request.get('/events', { params })
}

export function getEvent(id: number): Promise<Event> {
  return request.get(`/events/${id}`)
}

export function createEvent(data: Partial<Event>): Promise<Event> {
  return request.post('/events', data)
}

export function updateEvent(id: number, data: Partial<Event>): Promise<Event> {
  return request.put(`/events/${id}`, data)
}

export function getEventResources(eventId: number): Promise<EventResource[]> {
  return request.get(`/events/${eventId}/resources`)
}

export function addEventResource(eventId: number, data: Partial<EventResource>): Promise<EventResource> {
  return request.post(`/events/${eventId}/resources`, data)
}

export function removeEventResource(eventId: number, resourceId: number): Promise<void> {
  return request.delete(`/events/${eventId}/resources/${resourceId}`)
}

export function getStaffSchedule(params?: { date?: string; staff_id?: number; event_id?: number }): Promise<unknown[]> {
  return request.get('/events/staff-schedule', { params })
}

export function checkConflicts(params: {
  date: string
  venue_id?: number
  staff_ids?: string
  exclude_event_id?: number
}): Promise<{ has_conflicts: boolean; conflicts: string[] }> {
  return request.get('/events/conflicts', { params })
}
