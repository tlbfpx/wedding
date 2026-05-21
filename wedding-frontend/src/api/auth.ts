import request from './index'

export interface LoginParams {
  username: string
  password: string
}

export interface LoginResult {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserInfo {
  id: number
  username: string
  name: string
  team: string
  permissions: string[]
}

export function loginApi(data: LoginParams): Promise<LoginResult> {
  return request.post('/auth/login', data)
}

export function refreshTokenApi(refresh_token: string): Promise<LoginResult> {
  return request.post('/auth/refresh', { refresh_token })
}

export function logoutApi(): Promise<void> {
  return request.post('/auth/logout')
}

export function getMeApi(): Promise<UserInfo> {
  return request.get('/auth/me')
}
