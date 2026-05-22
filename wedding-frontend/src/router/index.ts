import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const MainLayout = () => import('@/layouts/MainLayout.vue')

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/permission-denied',
    name: 'PermissionDenied',
    component: () => import('@/views/system/PermissionDenied.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard',
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '工作台', module: 'dashboard' },
      },
      {
        path: 'customers',
        name: 'Customers',
        component: () => import('@/views/customers/CustomerList.vue'),
        meta: { title: '客户列表', module: 'customers' },
      },
      {
        path: 'customers/:id',
        name: 'CustomerDetail',
        component: () => import('@/views/customers/CustomerDetail.vue'),
        meta: { title: '客户详情', module: 'customers' },
      },
      {
        path: 'customer-pool',
        name: 'CustomerPool',
        component: () => import('@/views/customers/CustomerPool.vue'),
        meta: { title: '公海池', module: 'customers' },
      },
      {
        path: 'events',
        name: 'Events',
        component: () => import('@/views/events/EventList.vue'),
        meta: { title: '排期管理', module: 'events' },
      },
      {
        path: 'events/:id',
        name: 'EventDetail',
        component: () => import('@/views/events/EventDetail.vue'),
        meta: { title: '活动详情', module: 'events' },
      },
      {
        path: 'venues',
        name: 'Venues',
        component: () => import('@/views/events/VenueList.vue'),
        meta: { title: '场地管理', module: 'events' },
      },
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('@/views/Orders.vue'),
        meta: { title: '订单列表', module: 'orders' },
      },
      {
        path: 'orders/create',
        name: 'OrderCreate',
        component: () => import('@/views/OrderCreate.vue'),
        meta: { title: '新建订单', module: 'orders' },
      },
      {
        path: 'orders/:id',
        name: 'OrderDetail',
        component: () => import('@/views/OrderDetail.vue'),
        meta: { title: '订单详情', module: 'orders' },
      },
      {
        path: 'suppliers',
        name: 'Suppliers',
        component: () => import('@/views/suppliers/SupplierList.vue'),
        meta: { title: '供应商列表', module: 'suppliers' },
      },
      {
        path: 'suppliers/:id',
        name: 'SupplierDetail',
        component: () => import('@/views/suppliers/SupplierDetail.vue'),
        meta: { title: '供应商详情', module: 'suppliers' },
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/system/UserList.vue'),
        meta: { title: '员工管理', module: 'users' },
      },
      {
        path: 'roles',
        name: 'Roles',
        component: () => import('@/views/system/RoleList.vue'),
        meta: { title: '角色权限', module: 'roles' },
      },
      {
        path: 'operation-logs',
        name: 'OperationLogs',
        component: () => import('@/views/system/OperationLogs.vue'),
        meta: { title: '操作日志', module: 'users' },
      },
      {
        path: 'approvals',
        name: 'Approvals',
        component: () => import('@/views/Approvals.vue'),
        meta: { title: '审批管理', module: 'orders' },
      },
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import('@/views/system/Notifications.vue'),
        meta: { title: '消息通知' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  const token = localStorage.getItem('token')
  const authStore = useAuthStore()

  // Redirect to login if not authenticated
  if (to.meta.requiresAuth !== false && !token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  // Redirect to home if already logged in and trying to access login
  if (to.path === '/login' && token) {
    next({ path: '/' })
    return
  }

  // If authenticated, ensure user data is loaded before permission check
  if (token && !authStore.user) {
    try {
      await authStore.fetchUser()
    } catch {
      // If fetch fails, clear auth and redirect to login
      authStore.clearAuth()
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
  }

  // Check route-level permission if route has module meta
  const routeModule = to.meta.module as string | undefined
  if (routeModule) {
    // Module name mapping: frontend names to backend keys
    const moduleMap: Record<string, string> = {
      'customers': 'crm',
      'events': 'schedule',
      'orders': 'order',
      'suppliers': 'supplier',
      'users': 'system',
      'roles': 'system',
    }

    // Try both frontend module name and backend key
    const requiredPermission = `${routeModule}:read`
    const backendKey = moduleMap[routeModule]
    const backendPermission = backendKey ? `${backendKey}:read` : ''

    if (!authStore.hasPermission(requiredPermission) &&
        (!backendPermission || !authStore.hasPermission(backendPermission))) {
      // Redirect to permission denied page
      next({ path: '/permission-denied' })
      return
    }
  }

  next()
})

export default router
