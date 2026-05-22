import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const MainLayout = () => import('@/layouts/MainLayout.vue')

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
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
        meta: { title: '工作台' },
      },
      {
        path: 'customers',
        name: 'Customers',
        component: () => import('@/views/customers/CustomerList.vue'),
        meta: { title: '客户列表' },
      },
      {
        path: 'customers/:id',
        name: 'CustomerDetail',
        component: () => import('@/views/customers/CustomerDetail.vue'),
        meta: { title: '客户详情' },
      },
      {
        path: 'customer-pool',
        name: 'CustomerPool',
        component: () => import('@/views/customers/CustomerPool.vue'),
        meta: { title: '公海池' },
      },
      {
        path: 'events',
        name: 'Events',
        component: () => import('@/views/events/EventList.vue'),
        meta: { title: '排期管理' },
      },
      {
        path: 'events/:id',
        name: 'EventDetail',
        component: () => import('@/views/events/EventDetail.vue'),
        meta: { title: '活动详情' },
      },
      {
        path: 'venues',
        name: 'Venues',
        component: () => import('@/views/events/VenueList.vue'),
        meta: { title: '场地管理' },
      },
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('@/views/Orders.vue'),
        meta: { title: '订单列表' },
      },
      {
        path: 'orders/create',
        name: 'OrderCreate',
        component: () => import('@/views/OrderCreate.vue'),
        meta: { title: '新建订单' },
      },
      {
        path: 'orders/:id',
        name: 'OrderDetail',
        component: () => import('@/views/OrderDetail.vue'),
        meta: { title: '订单详情' },
      },
      {
        path: 'suppliers',
        name: 'Suppliers',
        component: () => import('@/views/suppliers/SupplierList.vue'),
        meta: { title: '供应商列表' },
      },
      {
        path: 'suppliers/:id',
        name: 'SupplierDetail',
        component: () => import('@/views/suppliers/SupplierDetail.vue'),
        meta: { title: '供应商详情' },
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/system/UserList.vue'),
        meta: { title: '员工管理' },
      },
      {
        path: 'roles',
        name: 'Roles',
        component: () => import('@/views/system/RoleList.vue'),
        meta: { title: '角色权限' },
      },
      {
        path: 'operation-logs',
        name: 'OperationLogs',
        component: () => import('@/views/system/OperationLogs.vue'),
        meta: { title: '操作日志' },
      },
      {
        path: 'approvals',
        name: 'Approvals',
        component: () => import('@/views/Approvals.vue'),
        meta: { title: '审批管理' },
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

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')

  if (to.meta.requiresAuth !== false && !token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  if (to.path === '/login' && token) {
    next({ path: '/' })
    return
  }

  next()
})

export default router
