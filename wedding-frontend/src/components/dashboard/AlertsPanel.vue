<script setup lang="ts">
import { ref, computed } from 'vue'
import { NCard, NSkeleton, NSpace, NTag, NButton, NButtonGroup, NCollapse, NCollapseItem } from 'naive-ui'
import type { AlertsResponse, AlertItem } from '@/api/dashboard'
import { resolveAlert } from '@/api/dashboard'

interface Props {
  loading?: boolean
  data?: AlertsResponse
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
})

const emit = defineEmits<{
  resolved: [alertId: string]
}>()

const resolving = ref<Set<string>>(new Set())
const collapsed = ref(false)

const highAlerts = computed<AlertItem[]>(() => {
  return props.data?.alerts.filter(a => a.level === 'high') || []
})

const mediumAlerts = computed<AlertItem[]>(() => {
  return props.data?.alerts.filter(a => a.level === 'medium') || []
})

const displayAlerts = computed(() => {
  const result: AlertItem[] = []
  if (!collapsed.value) {
    result.push(...highAlerts.value.slice(0, 10))
    result.push(...mediumAlerts.value.slice(0, 10))
  }
  return result
})

async function handleResolve(alert: AlertItem) {
  if (resolving.value.has(alert.id)) return

  resolving.value.add(alert.id)
  try {
    await resolveAlert(alert.id, {})
    emit('resolved', alert.id)
  } catch (error) {
    console.error('Failed to resolve alert:', error)
  } finally {
    resolving.value.delete(alert.id)
  }
}

function handleViewDetail(alert: AlertItem) {
  // 根据实体类型跳转到相应页面
  switch (alert.entity_type) {
    case 'order':
      // 跳转到订单详情
      window.location.href = `/orders/${alert.entity_id}`
      break
    case 'event':
      // 跳转到活动详情
      window.location.href = `/events/${alert.entity_id}`
      break
    case 'customer':
      // 跳转到客户详情
      window.location.href = `/customers/${alert.entity_id}`
      break
    default:
      console.warn('Unknown entity type:', alert.entity_type)
  }
}

function getAlertColor(level: string): 'error' | 'warning' | 'default' {
  switch (level) {
    case 'high':
      return 'error'
    case 'medium':
      return 'warning'
    case 'low':
      return 'default'
    default:
      return 'default'
  }
}

function getAlertIcon(level: string): string {
  switch (level) {
    case 'high':
      return '🔴'
    case 'medium':
      return '🟡'
    case 'low':
      return '🟢'
    default:
      return '⚪'
  }
}

function formatTime(time: string): string {
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const days = Math.floor(hours / 24)

  if (days > 0) {
    return `${days}天前`
  } else if (hours > 0) {
    return `${hours}小时前`
  } else {
    const minutes = Math.floor(diff / (1000 * 60))
    return `${minutes}分钟前`
  }
}
</script>

<template>
  <NCard title="风险预警">
    <template #header-extra>
      <NSpace>
        <NTag v-if="data?.high_count" type="error" size="small">
          🔴 高风险 {{ data.high_count }}
        </NTag>
        <NTag v-if="data?.medium_count" type="warning" size="small">
          🟡 中风险 {{ data.medium_count }}
        </NTag>
        <NTag v-if="data?.low_count" type="default" size="small">
          🟢 低风险 {{ data.low_count }}
        </NTag>
      </NSpace>
    </template>

    <NSkeleton v-if="loading" text :repeat="6" />
    <template v-else>
      <div v-if="displayAlerts.length === 0" style="text-align: center; color: #999; padding: 40px 0">
        <div style="font-size: 48px; margin-bottom: 16px">✓</div>
        <div>暂无风险预警</div>
      </div>

      <NCollapse v-else>
        <NCollapseItem v-for="alert in displayAlerts" :key="alert.id" :default-expanded="highAlerts.length > 0 ? alert.level === 'high' : false">
          <template #header>
            <NSpace align="center">
              <span>{{ getAlertIcon(alert.level) }}</span>
              <span style="font-weight: 500">{{ alert.title }}</span>
              <NTag :type="getAlertColor(alert.level)" size="tiny">{{ alert.level }}</NTag>
            </NSpace>
          </template>
          <template #header-extra>
            <span style="font-size: 12px; color: #999">{{ formatTime(alert.created_at) }}</span>
          </template>

          <div style="padding: 8px 0">
            <div style="font-size: 13px; color: #666; margin-bottom: 12px">
              {{ alert.detail }}
            </div>
            <div v-if="alert.owner_name" style="font-size: 12px; color: #999; margin-bottom: 12px">
              负责人：{{ alert.owner_name }}
            </div>
            <NButtonGroup size="small">
              <NButton @click="handleViewDetail(alert)">查看详情</NButton>
              <NButton
                v-if="alert.actions.includes('mark_resolved')"
                type="primary"
                :loading="resolving.has(alert.id)"
                @click="handleResolve(alert)"
              >
                标记已处理
              </NButton>
            </NButtonGroup>
          </div>
        </NCollapseItem>
      </NCollapse>

      <div v-if="data && data.total > displayAlerts.length" style="text-align: center; margin-top: 12px">
        <NButton text type="primary" size="small">
          查看全部 {{ data.total }} 条预警
        </NButton>
      </div>
    </template>
  </NCard>
</template>
