<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { NBadge, NIcon, NPopover, NButton, NEmpty, NSpin, NSpace, NTag, NDivider } from 'naive-ui'
import { NotificationsOutline } from '@vicons/ionicons5'
import { useRouter } from 'vue-router'
import { getNotifications, getUnreadCount, markAsRead, markAllAsRead } from '@/api/notifications'
import type { Notification } from '@/api/notifications'

const router = useRouter()
const unreadCount = ref(0)
const notifications = ref<Notification[]>([])
const loading = ref(false)
const showPopover = ref(false)
let timer: number | null = null

async function fetchUnreadCount() {
  try {
    const res = await getUnreadCount()
    unreadCount.value = res.count
  } catch {}
}

async function fetchNotifications() {
  loading.value = true
  try {
    const res = await getNotifications({ page: 1, page_size: 10 })
    notifications.value = res.items || []
  } catch {} finally {
    loading.value = false
  }
}

async function handleOpenPopover(open: boolean) {
  if (open) {
    await fetchNotifications()
  }
}

async function handleMarkAllRead() {
  await markAllAsRead()
  await fetchUnreadCount()
  await fetchNotifications()
}

async function handleClickNotification(item: Notification) {
  if (!item.is_read) {
    await markAsRead([item.id])
  }
  showPopover.value = false

  if (item.related_type === 'approval') {
    router.push('/approvals')
  } else if (item.related_type === 'event') {
    if (item.related_id) {
      router.push(`/events/${item.related_id}`)
    } else {
      router.push('/events')
    }
  } else if (item.related_type === 'customer') {
    if (item.related_id) {
      router.push(`/customers/${item.related_id}`)
    } else {
      router.push('/customers')
    }
  }
}

function formatTime(dateStr: string | null) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour}小时前`
  const diffDay = Math.floor(diffHour / 24)
  if (diffDay < 30) return `${diffDay}天前`
  return d.toLocaleDateString()
}

function getTypeLabel(type: string) {
  const map: Record<string, string> = {
    approval: '审批',
    schedule: '排期',
    follow_up: '跟进',
    system: '系统',
  }
  return map[type] || type
}

function getTypeColor(type: string) {
  const map: Record<string, string> = {
    approval: 'warning',
    schedule: 'info',
    follow_up: 'success',
    system: 'default',
  }
  return (map[type] || 'default') as any
}

onMounted(() => {
  fetchUnreadCount()
  timer = window.setInterval(fetchUnreadCount, 30000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <NPopover
    trigger="click"
    :width="380"
    placement="bottom-end"
    v-model:show="showPopover"
    @update:show="handleOpenPopover"
  >
    <template #trigger>
      <NBadge :value="unreadCount" :max="99">
        <NIcon size="20" style="cursor: pointer">
          <NotificationsOutline />
        </NIcon>
      </NBadge>
    </template>
    <div style="max-height: 400px; overflow-y: auto">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px">
        <span style="font-weight: 600; font-size: 15px">消息通知</span>
        <NButton v-if="unreadCount > 0" text size="small" type="primary" @click="handleMarkAllRead">
          全部已读
        </NButton>
      </div>
      <NSpin :show="loading">
        <NEmpty v-if="notifications.length === 0 && !loading" description="暂无通知" />
        <div v-else>
          <div
            v-for="item in notifications"
            :key="item.id"
            style="padding: 10px 0; cursor: pointer; border-bottom: 1px solid #f0f0f0"
            :style="{ background: item.is_read ? 'transparent' : '#f6ffed' }"
            @click="handleClickNotification(item)"
          >
            <NSpace justify="space-between" align="center">
              <NTag :type="getTypeColor(item.type)" size="small">{{ getTypeLabel(item.type) }}</NTag>
              <span style="font-size: 12px; color: #999">{{ formatTime(item.created_at) }}</span>
            </NSpace>
            <div style="margin-top: 6px; font-size: 14px; font-weight: 500">{{ item.title }}</div>
            <div style="margin-top: 4px; font-size: 13px; color: #666; line-height: 1.4">{{ item.content }}</div>
          </div>
        </div>
      </NSpin>
      <NDivider style="margin: 8px 0" />
      <NButton text block type="primary" @click="router.push('/notifications'); showPopover = false">
        查看全部通知
      </NButton>
    </div>
  </NPopover>
</template>
