<script setup lang="ts">
import { h, ref, computed } from 'vue'
import type { Component } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  NLayout,
  NLayoutSider,
  NLayoutHeader,
  NLayoutContent,
  NMenu,
  NBreadcrumb,
  NBreadcrumbItem,
  NDropdown,
  NAvatar,
  NSpace,
  NIcon,
} from 'naive-ui'
import type { MenuOption } from 'naive-ui'
import {
  HomeOutline,
  PeopleOutline,
  CalendarOutline,
  DocumentTextOutline,
  BusinessOutline,
  PersonOutline,
  SettingsOutline,
  LogOutOutline,
} from '@vicons/ionicons5'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const collapsed = ref(false)

function renderIcon(icon: Component) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions: MenuOption[] = [
  {
    label: '工作台',
    key: '/dashboard',
    icon: renderIcon(HomeOutline),
  },
  {
    label: '客户管理',
    key: 'customer-group',
    icon: renderIcon(PeopleOutline),
    children: [
      { label: '客户列表', key: '/customers' },
      { label: '公海池', key: '/customer-pool' },
    ],
  },
  {
    label: '排期管理',
    key: '/events',
    icon: renderIcon(CalendarOutline),
  },
  {
    label: '订单管理',
    key: 'order-group',
    icon: renderIcon(DocumentTextOutline),
    children: [
      { label: '订单列表', key: '/orders' },
      { label: '新建订单', key: '/orders/create' },
    ],
  },
  {
    label: '供应商管理',
    key: '/suppliers',
    icon: renderIcon(BusinessOutline),
  },
  {
    label: '员工管理',
    key: '/users',
    icon: renderIcon(PersonOutline),
  },
  {
    label: '系统设置',
    key: 'system-group',
    icon: renderIcon(SettingsOutline),
    children: [
      { label: '角色权限', key: '/roles' },
      { label: '操作日志', key: '/operation-logs' },
      { label: '审批管理', key: '/approvals' },
    ],
  },
]

const activeKey = computed(() => route.path)

const userDropdownOptions = [
  { label: '退出登录', key: 'logout', icon: renderIcon(LogOutOutline) },
]

function handleMenuUpdate(key: string) {
  router.push(key)
}

function handleUserDropdown(key: string) {
  if (key === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}

const breadcrumbItems = computed(() => {
  const matched = route.matched.filter((r) => r.meta?.title)
  return matched.map((r) => r.meta.title as string)
})
</script>

<template>
  <NLayout has-sider style="height: 100vh">
    <NLayoutSider
      bordered
      collapse-mode="width"
      :collapsed-width="64"
      :width="220"
      :collapsed="collapsed"
      show-trigger
      @collapse="collapsed = true"
      @expand="collapsed = false"
      :native-scrollbar="false"
      style="background-color: #001529"
    >
      <div
        style="
          height: 48px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #fff;
          font-size: 18px;
          font-weight: 600;
          white-space: nowrap;
          overflow: hidden;
        "
      >
        <span v-if="!collapsed">婚礼管理系统</span>
        <span v-else>婚</span>
      </div>
      <NMenu
        :value="activeKey"
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        :inverted="true"
        @update:value="handleMenuUpdate"
      />
    </NLayoutSider>
    <NLayout>
      <NLayoutHeader bordered style="height: 48px; display: flex; align-items: center; padding: 0 24px; justify-content: space-between">
        <NBreadcrumb>
          <NBreadcrumbItem v-for="(item, index) in breadcrumbItems" :key="index">
            {{ item }}
          </NBreadcrumbItem>
        </NBreadcrumb>
        <NDropdown :options="userDropdownOptions" @select="handleUserDropdown">
          <NSpace align="center" style="cursor: pointer">
            <NAvatar :size="28" round style="background-color: #2080f0">
              {{ authStore.user?.name?.charAt(0) || 'U' }}
            </NAvatar>
            <span style="font-size: 14px">{{ authStore.user?.name || '用户' }}</span>
          </NSpace>
        </NDropdown>
      </NLayoutHeader>
      <NLayoutContent
        content-style="padding: 24px; background: #f5f5f5; min-height: calc(100vh - 48px)"
        :native-scrollbar="false"
      >
        <router-view />
      </NLayoutContent>
    </NLayout>
  </NLayout>
</template>
