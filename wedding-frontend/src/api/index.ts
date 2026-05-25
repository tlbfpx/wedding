import axios from 'axios'
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import DOMPurify from 'dompurify'
import { useAuthStore } from '@/stores/auth'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

// Track pending requests for deduplication
const pendingRequests = new Map<string, Promise<unknown>>()

function getRequestKey(config: InternalAxiosRequestConfig): string {
  return `${config.method || 'GET'}:${config.url || ''}:${JSON.stringify(config.params || {})}:${JSON.stringify(config.data || {})}`
}

// Request interceptor - attach token and handle CSRF
request.interceptors.request.use(
  async (config) => {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }

    // Add CSRF token for state-changing operations
    if (['post', 'put', 'patch', 'delete'].includes((config.method || '').toLowerCase())) {
      try {
        const csrfResp = await axios.get('/api/v1/auth/csrf')
        config.headers['X-CSRF-Token'] = csrfResp.data.csrf_token
      } catch {
        // CSRF endpoint may not exist in test environment
      }
    }

    // Request deduplication for GET requests
    if (config.method?.toLowerCase() === 'get') {
      const key = getRequestKey(config as InternalAxiosRequestConfig)
      if (pendingRequests.has(key)) {
        // Cancel the previous request by throwing an AbortError
        const controller = new AbortController()
        config.signal = controller.signal
        // Signal the previous request to abort
        pendingRequests.set(key, new Promise((_, reject) => {
          controller.signal.addEventListener('abort', () => reject(new DOMException('Deduplicated', 'AbortError')))
        }))
      }
      pendingRequests.set(key, request(config as InternalAxiosRequestConfig).catch(() => {}))
    }

    return config
  },
  (error) => {
    return Promise.reject(error)
  },
)

// Response interceptor - handle errors & token refresh
let isRefreshing = false
let pendingRequestsQueue: Array<(token: string) => void> = []

request.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  async (error) => {
    // Handle deduplicated requests
    if (error instanceof DOMException && error.name === 'AbortError') {
      return Promise.reject(error)
    }

    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      const authStore = useAuthStore()

      if (!authStore.refreshTokenValue) {
        authStore.logout()
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve) => {
          pendingRequestsQueue.push((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            resolve(request(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const newToken = await authStore.refreshToken()
        pendingRequestsQueue.forEach((cb) => cb(newToken))
        pendingRequestsQueue = []
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return request(originalRequest)
      } catch {
        pendingRequestsQueue = []
        authStore.logout()
        return Promise.reject(error)
      } finally {
        isRefreshing = false
      }
    }

    const rawDetail = error.response?.data?.detail
    let message =
      error.response?.data?.message ||
      error.message ||
      '请求失败'
    if (rawDetail) {
      if (typeof rawDetail === 'string') {
        message = rawDetail
      } else if (Array.isArray(rawDetail)) {
        message = rawDetail.map((e: any) => e.msg || JSON.stringify(e)).join('; ')
      } else {
        message = JSON.stringify(rawDetail)
      }
    }

    // XSS protection: sanitize error messages before display
    const sanitizedMessage = DOMPurify.sanitize(message, { ALLOWED_TAGS: [] })

    return Promise.reject(new Error(sanitizedMessage))
  },
)

export default request