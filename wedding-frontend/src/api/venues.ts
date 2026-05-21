import request from './index'

export interface Venue {
  id: number
  name: string
  address?: string
  capacity?: number
  contact?: string
  phone?: string
  price?: number
  note?: string
  created_at: string
  updated_at: string
}

export interface VenueAvailability {
  venue_id: number
  date_start: string
  date_end: string
  booked_dates: string[]
  available: boolean
}

export interface VenueListParams {
  page?: number
  page_size?: number
  keyword?: string
  capacity_min?: number
}

export interface PaginatedResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export function getVenues(params?: VenueListParams): Promise<PaginatedResult<Venue>> {
  return request.get('/venues', { params })
}

export function getVenue(id: number): Promise<Venue> {
  return request.get(`/venues/${id}`)
}

export function createVenue(data: Partial<Venue>): Promise<Venue> {
  return request.post('/venues', data)
}

export function updateVenue(id: number, data: Partial<Venue>): Promise<Venue> {
  return request.put(`/venues/${id}`, data)
}

export function checkVenueAvailability(
  venueId: number,
  dateStart: string,
  dateEnd: string,
): Promise<VenueAvailability> {
  return request.get(`/venues/${venueId}/availability`, {
    params: { date_start: dateStart, date_end: dateEnd },
  })
}
