<script setup lang="ts">
import { computed } from 'vue'
import { NCard, NGrid, NGi, NSkeleton, NStatistic, NProgress, NSpace, NTag } from 'naive-ui'
import type { MetricValue } from '@/api/dashboard'

interface Props {
  loading?: boolean
  metrics?: {
    revenue: MetricValue
    orders: MetricValue
    avg_order_value: MetricValue
    sign_rate: MetricValue
    gross_profit: MetricValue
  }
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
})

interface MetricCard {
  label: string
  value: MetricValue
  format: 'currency' | 'number' | 'percent'
}

const metricCards = computed<MetricCard[]>((() => {
  if (!props.metrics) return []
  return [
    {
      label: '营收',
      value: props.metrics.revenue,
      format: 'currency',
    },
    {
      label: '订单',
      value: props.metrics.orders,
      format: 'number',
    },
    {
      label: '客单价',
      value: props.metrics.avg_order_value,
      format: 'currency',
    },
    {
      label: '签约率',
      value: props.metrics.sign_rate,
      format: 'percent',
    },
    {
      label: '毛利',
      value: props.metrics.gross_profit,
      format: 'currency',
    },
  ]
})())

function formatValue(value: number, format: string): string {
  switch (format) {
    case 'currency':
      return '¥' + value.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
    case 'percent':
      return (value * 100).toFixed(0) + '%'
    case 'number':
    default:
      return value.toLocaleString('zh-CN')
  }
}

function getTrendIcon(trend?: number): string {
  if (trend === undefined) return ''
  return trend > 0 ? '▲' : trend < 0 ? '▼' : ''
}

function getTrendColor(trend?: number): string {
  if (trend === undefined) return '#999'
  return trend > 0 ? '#18a058' : trend < 0 ? '#d03050' : '#999'
}

function getTrendLabel(trend?: number): string {
  if (trend === undefined) return ''
  const absTrend = Math.abs(trend * 100)
  return `${absTrend.toFixed(1)}%`
}

function getAchievementStatus(achievement?: number): 'success' | 'warning' | 'error' | undefined {
  if (achievement === undefined) return undefined
  if (achievement >= 0.8) return 'success'
  if (achievement >= 0.6) return 'warning'
  return 'error'
}
</script>

<template>
  <NCard title="经营健康度">
    <NSkeleton v-if="loading" text :repeat="5" />
    <NGrid v-else :x-gap="16" :y-gap="16" :cols="5" :x-span="24" responsive="screen">
      <NGi v-for="card in metricCards" :key="card.label">
        <div style="text-align: center; padding: 8px 0">
          <div style="font-size: 13px; color: #666; margin-bottom: 8px">{{ card.label }}</div>
          <div style="font-size: 24px; font-weight: 600; margin-bottom: 4px">
            {{ formatValue(card.value.value, card.format) }}
          </div>
          <div v-if="card.value.trend !== undefined" style="font-size: 12px; margin-bottom: 8px">
            <span
              :style="{
                color: getTrendColor(card.value.trend),
                fontWeight: 500,
              }"
            >
              {{ getTrendIcon(card.value.trend) }} {{ getTrendLabel(card.value.trend) }}
            </span>
          </div>
          <div v-if="card.value.achievement !== undefined" style="margin-top: 8px">
            <NProgress
              type="line"
              :percentage="card.value.achievement * 100"
              :show-indicator="false"
              :height="6"
              :rail-color="'#f0f0f0'"
            />
            <div style="font-size: 12px; color: #999; margin-top: 4px">
              {{ (card.value.achievement * 100).toFixed(0) }}% 达成
            </div>
          </div>
        </div>
      </NGi>
    </NGrid>
    <div v-if="!loading && metricCards.length === 0" style="text-align: center; color: #999; padding: 40px 0">
      暂无数据
    </div>
  </NCard>
</template>
