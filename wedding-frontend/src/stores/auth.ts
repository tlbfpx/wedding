import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { loginApi, refreshTokenApi, logoutApi, getMeApi } from '@/api/auth'
import type { UserInfo } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const refreshTokenValue = ref<string>(localStorage.getItem('refreshToken') || '')
  const user = ref<UserInfo | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const permissions = computed(() => user.value?.permissions || [])

  function setTokens(access: string, refresh: string) {
    token.value = access
    refreshTokenValue.value = refresh
    localStorage.setItem('token', access)
    localStorage.setItem('refreshToken', refresh)
  }

  function clearAuth() {
    token.value = ''
    refreshTokenValue.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
  }

  async function login(username: string, password: string) {
    const res = await loginApi({ username, password })
    setTokens(res.access_token, res.refresh_token)
    await fetchUser()
  }

  async function logout() {
    try {
      await logoutApi()
    } catch {
      // ignore errors on logout
    } finally {
      clearAuth()
    }
  }

  async function fetchUser() {
    const res = await getMeApi()
    user.value = res
  }

  async function refreshToken(): Promise<string> {
    const res = await refreshTokenApi(refreshTokenValue.value)
    setTokens(res.access_token, res.refresh_token)
    return res.access_token
  }

  function hasPermission(permission: string): boolean {
    return permissions.value.includes(permission)
  }

  function hasAnyPermission(perms: string[]): boolean {
    return perms.some(p => permissions.value.includes(p))
  }

  function hasModuleAccess(module: string): boolean {
    return permissions.value.some(p => p.startsWith(`${module}:`))
  }

  return {
    token,
    refreshTokenValue,
    user,
    isLoggedIn,
    permissions,
    login,
    logout,
    fetchUser,
    refreshToken,
    hasPermission,
    hasAnyPermission,
    hasModuleAccess,
    clearAuth,
  }
})
