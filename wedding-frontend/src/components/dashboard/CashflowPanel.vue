<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { NCard, NSkeleton, NGrid, NGi, NStatistic, NSpace, NProgress, NTag, NButton } from 'naive-ui'
import type { CashflowResponse } from '@/api/dashboard'

interface Props {
  loading?: boolean
  data?: CashflowResponse
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
})

const router = useRouter()

const paymentMethodLabels: Record<string, string> = {
  wechat: '微信支付',
  bank: '银行转账',
  cash: '现金',
  alipay: '支付宝',
  other: '其他',
}

const paymentMethods = computed(() => {
  if (!props.data?.cash_in.by_method) return []
  return Object.entries(props.data.cash_in.by_method)
    .map(([method, amount]) => ({
      method,
      amount,
      label: paymentMethodLabels[method] || method,
      percent: (amount / props.data!.cash_in.total) * 100,
    }))
    .sort((a, b) => b.amount - a.amount)
})

const agingBuckets = computed(() => {
  return props.data?.aging || []
})

const hasOverdue = computed(() => {
  return (props.data?.receivables.overdue || 0) > 0
})

const overdueLevel = computed(() => {
  const overdue = props.data?.receivables.overdue || 0
  if (overdue > 100000) return 'error'  // > 10万
  if (overdue > 50000) return 'warning'  // > 5万
  return undefined
})

function formatAmount(amount: number): string {
  return '¥' + amount.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function gotoReceivables() {
  router.push('/finance/receivables')
}
</script>

<template>
  <NCard title="现金流与应收">
    <NSkeleton v-if="loading" text :repeat="8" />
    <template v-else>
      <!-- 顶部指标 -->
      <NGrid :x-gap="16" :y-gap="12" :cols="4" style="margin-bottom: 24px">
        <NGi>
          <NStatistic label="现金流入" :value="formatAmount(data?.cash_in.total || 0)" />
        </NGi>
        <NGi>
          <NStatistic label="应收余额" :value="formatAmount(data?.receivables.total || 0)" />
        </NGi>
        <NGi>
          <NStatistic
            label="逾期应收"
            :value="formatAmount(data?.receivables.overdue || 0)"
            :style="{ color: hasOverdue ? '#d03050' : undefined }"
          >
            <template #suffix>
              <NTag v-if="hasOverdue" :type="overdueLevel" size="small">
                {{ data?.receivables.overdue_count || 0 }} 笔
              </NTag>
            </template>
          </NStatistic>
        </NGi>
        <NGi>
          <NStatistic label="周转天数" :value="data?.turnover_days || 0">
            <template #suffix>天</template>
          </NStatistic>
        </NGi>
      </NGrid>

      <!-- 付款方式分布 + 应收账龄 -->
      <NGrid :x-gap="24" :y-gap="16" :cols="2">
        <NGi>
          <div style="font-size: 14px; font-weight: 500; margin-bottom: 12px">付款方式分布</div>
          <NSpace vertical :size="8">
            <div v-for="item in paymentMethods" :key="item.method" style="display: flex; align-items: center; gap: 8px">
              <div style="width: 80px; font-size: 13px">{{ item.label }}</div>
              <NProgress
                type="line"
                :percentage="item.percent"
                :show-indicator="false"
                :height="16"
                :rail-color="'#f0f0f0'"
                :color="'#18a058'"
              />
              <div style="width: 80px; text-align: right; font-size: 13px; color: #666">
                {{ item.percent.toFixed(0) }}%
              </div>
            </div>
          </NSpace>
        </NGi>
        <NGi>
          <div style="font-size: 14px; font-weight: 500; margin-bottom: 12px">应收账龄分析</div>
          <NSpace vertical :size="8">
            <div v-for="bucket in agingBuckets" :key="bucket.bucket" style="display: flex; align-items: center; gap: 8px">
              <div style="width: 80px; font-size: 13px">{{ bucket.bucket }} 天</div>
              <NProgress
                type="line"
                :percentage="bucket.percent"
                :show-indicator="false"
                :height="16"
                :rail-color="'#f0f0f0'"
                :color="bucket.bucket === '90+' ? '#d03050' : '#18a058'"
              />
              <div style="width: 80px; text-align: right; font-size: 13px; color: #666">
                {{ bucket.percent.toFixed(0) }}%
              </div>
            </div>
          </NSpace>
        </NGi>
      </NGrid>

      <!-- 操作按钮 -->
      <NSpace style="margin-top: 16px">
        <NButton size="small" @click="gotoReceivables">查看应收明细</NButton>
      </NSpace>
    </template>
  </NCard>
</template>
