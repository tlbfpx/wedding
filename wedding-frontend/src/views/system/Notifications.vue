<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  NPageHeader,
  NCard,
  NSpace,
  NButton,
  NList,
  NListItem,
  NTag,
  NPagination,
  NTabs,
  NTabPane,
  NEmpty,
  NSpin,
  useMessage,
} from 'naive-ui'
import { getNotifications, markAsRead, markAllAsRead } from '@/api/notifications'
import type { Notification } from '@/api/notifications'

const router = useRouter()
const message = useMessage()

const loading = ref(false)
const notifications = ref<Notification[]>([])
const total = ref(0)
const pagination = reactive({
  page: 1,
  pageSize: 20,
})

const typeFilter = ref<string | null>(null)
const readFilter = ref<string | null>(null)

const typeOptions = [
  { label: '审批', value: 'approval' },
  { label: '排期', value: 'schedule' },
  { label: '跟进', value: 'follow_up' },
  { label: '系统', value: 'system' },
]

const typeLabelMap: Record<string, string> = {
  approval: '审批',
  schedule: '排期',
  follow_up: '跟进',
  system: '系统',
}

const typeColorMap: Record<string, string> = {
  approval: 'warning',
  schedule: 'info',
  follow_up: 'success',
  system: 'default',
}

async function fetchNotifications() {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (typeFilter.value) {
      params.type = typeFilter.value
    }
    if (readFilter.value === 'unread') {
      params.is_read = false
    } else if (readFilter.value === 'read') {
      params.is_read = true
    }
    const res = await getNotifications(params)
    notifications.value = res.items || []
    total.value = res.total || 0
  } catch (err: any) {
    message.error(err.message || '获取通知列表失败')
  } finally {
    loading.value = false
  }
}

async function handleMarkAllRead() {
  try {
    await markAllAsRead()
    message.success('已全部标记为已读')
    await fetchNotifications()
  } catch (err: any) {
    message.error(err.message || '操作失败')
  }
}

async function handleClickNotification(item: Notification) {
  if (!item.is_read) {
    try {
      await markAsRead([item.id])
      item.is_read = true
    } catch {}
  }

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

function handlePageChange(page: number) {
  pagination.page = page
  fetchNotifications()
}

function handlePageSizeChange(pageSize: number) {
  pagination.pageSize = pageSize
  pagination.page = 1
  fetchNotifications()
}

function handleTypeChange(value: string) {
  typeFilter.value = value || null
  pagination.page = 1
  fetchNotifications()
}

function handleReadFilterChange(value: string) {
  readFilter.value = value || null
  pagination.page = 1
  fetchNotifications()
}

function formatTime(dateStr: string | null) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleString('zh-CN')
}

const hasUnread = computed(() => notifications.value.some((n) => !n.is_read))

onMounted(() => {
  fetchNotifications()
})
</script>

<template>
  <div>
    <NPageHeader title="消息通知">
      <template #extra>
        <NButton type="primary" @click="handleMarkAllRead">全部已读</NButton>
      </template>
    </NPageHeader>

    <NCard style="margin-top: 16px">
      <!-- Filters -->
      <NSpace vertical :size="16">
        <NSpace align="center" :wrap="true">
          <span style="font-size: 14px; color: #666">类型：</span>
          <NTabs
            type="segment"
            size="small"
            :value="typeFilter || 'all'"
            @update:value="handleTypeChange"
            style="width: 400px"
          >
            <NTabPane name="all" tab="全部" />
            <NTabPane v-for="opt in typeOptions" :key="opt.value" :name="opt.value" :tab="opt.label" />
          </NTabs>
        </NSpace>
        <NSpace align="center" :wrap="true">
          <span style="font-size: 14px; color: #666">状态：</span>
          <NTabs
            type="segment"
            size="small"
            :value="readFilter || 'all'"
            @update:value="handleReadFilterChange"
            style="width: 280px"
          >
            <NTabPane name="all" tab="全部" />
            <NTabPane name="unread" tab="未读" />
            <NTabPane name="read" tab="已读" />
          </NTabs>
        </NSpace>
      </NSpace>

      <!-- Notification list -->
      <NSpin :show="loading" style="margin-top: 16px">
        <NEmpty v-if="notifications.length === 0 && !loading" description="暂无通知" />
        <NList v-else bordered>
          <NListItem
            v-for="item in notifications"
            :key="item.id"
            style="cursor: pointer; transition: background 0.2s"
            :style="{ background: item.is_read ? 'transparent' : '#f6ffed' }"
            @click="handleClickNotification(item)"
          >
            <template #prefix>
              <NTag :type="(typeColorMap[item.type] || 'default') as any" size="small">
                {{ typeLabelMap[item.type] || item.type }}
              </NTag>
            </template>
            <NSpace vertical :size="4">
              <NSpace justify="space-between" align="center">
                <span :style="{ fontWeight: item.is_read ? 400 : 600, fontSize: '14px' }">{{ item.title }}</span>
                <span style="font-size: 12px; color: #999">{{ formatTime(item.created_at) }}</span>
              </NSpace>
              <span style="font-size: 13px; color: #666; line-height: 1.4">{{ item.content }}</span>
            </NSpace>
            <template #suffix>
              <NButton v-if="!item.is_read" text size="small" type="primary" @click.stop="handleClickNotification(item)">
                标记已读
              </NButton>
            </template>
          </NListItem>
        </NList>
      </NSpin>

      <!-- Pagination -->
      <NSpace justify="end" style="margin-top: 16px">
        <NPagination
          :page="pagination.page"
          :page-size="pagination.pageSize"
          :item-count="total"
          :page-sizes="[10, 20, 50]"
          show-size-picker
          @update:page="handlePageChange"
          @update:page-size="handlePageSizeChange"
        />
      </NSpace>
    </NCard>
  </div>
</template>
