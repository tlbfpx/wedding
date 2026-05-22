import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { loginApi, refreshTokenApi, logoutApi, getMeApi } from '@/api/auth'
import type { UserInfo } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const refreshTokenValue = ref<string>(localStorage.getItem('refreshToken') || '')
  const user = ref<UserInfo | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const permissions = computed(() => user.value?.permissions || {})
  const permissionsMap = computed(() => user.value?.permissions || {})

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
    // permission can be like "dashboard", "customers", "crm", "crm:read"
    const perms = permissionsMap.value
    if (!perms) return false

    // Module name mapping: frontend names to backend keys
    const moduleMap: Record<string, string> = {
      'customers': 'crm',
      'events': 'schedule',
      'orders': 'order',
      'suppliers': 'supplier',
      'users': 'system',
      'roles': 'system',
    }

    // Check direct permission (exact match in perms)
    const checkDirect = (perm: string): boolean => {
      if (typeof perms === 'object' && perms !== null) {
        const value = perms[perm]
        if (value === true || value === 'all') return true
        // Also check if it's an object with any 'all' value
        if (typeof value === 'object' && value !== null) {
          return Object.values(value).some(v => v === 'all')
        }
      }
      return false
    }

    // First check direct (for "dashboard", "crm", "system", etc.)
    if (checkDirect(permission)) return true

    // Handle "module:action" format (e.g., "customers:read", "crm:read")
    if (permission.includes(':')) {
      const [module, action] = permission.split(':')
      const mappedModule = moduleMap[module] || module
      const modulePerms = (typeof perms === 'object' && perms !== null) ? perms[mappedModule] : undefined
      if (modulePerms !== undefined) {
        // If module has "all" permission, grant any action
        if (modulePerms === true || modulePerms === 'all') return true
        // If module has object permissions, check the action
        if (typeof modulePerms === 'object' && modulePerms !== null) {
          return modulePerms[action] === 'all'
        }
      }
      // Also check direct (mappedModule:action)
      return checkDirect(`${mappedModule}:${action}`)
    }

    // For module names (no colon), also check mapped name
    const mappedKey = moduleMap[permission]
    if (mappedKey && checkDirect(mappedKey)) return true

    return false
  }

  function hasAnyPermission(perms: string[]): boolean {
    return perms.some(p => hasPermission(p))
  }

  function hasModuleAccess(module: string): boolean {
    const perms = permissionsMap.value
    if (!perms) return false

    // Module name mapping
    const moduleMap: Record<string, string> = {
      'customers': 'crm',
      'events': 'schedule',
      'orders': 'order',
    }

    const checkModule = (m: string): boolean => {
      if (typeof perms === 'object' && perms !== null) {
        return m in perms
      }
      if (Array.isArray(perms)) {
        return perms.some(p => p.startsWith(`${m}:`))
      }
      return false
    }

    // Check direct
    if (checkModule(module)) return true

    // Check mapped name
    const mappedKey = moduleMap[module]
    if (mappedKey && checkModule(mappedKey)) return true

    return false
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
