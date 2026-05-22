<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  NCard,
  NGrid,
  NGi,
  NStatistic,
  NSkeleton,
  NSpace,
  NList,
  NListItem,
  NThing,
  NTag,
  NDataTable,
  NProgress,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import {
  getOverview,
  getSalesRanking,
  getConversionFunnel,
  getFinanceSummary,
  getScheduleHeatmap,
  getSupplierRanking,
} from '@/api/dashboard'
import { getEvents as getEventList } from '@/api/events'
import type {
  OverviewData,
  SalesRankingItem,
  ConversionFunnel,
  FinanceSummary,
  ScheduleHeatmapResult,
  SupplierRankingItem,
} from '@/api/dashboard'
import type { Event } from '@/api/events'

function formatAmount(amount: number): string {
  return '¥' + amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// Loading states per section
const overviewLoading = ref(true)
const salesLoading = ref(true)
const funnelLoading = ref(true)
const financeLoading = ref(true)
const heatmapLoading = ref(true)
const supplierLoading = ref(true)
const eventsLoading = ref(true)

// Data
const overview = ref<OverviewData | null>(null)
const salesRanking = ref<SalesRankingItem[]>([])
const funnelData = ref<ConversionFunnel | null>(null)
const financeData = ref<FinanceSummary | null>(null)
const heatmapData = ref<ScheduleHeatmapResult | null>(null)
const supplierRanking = ref<SupplierRankingItem[]>([])
const recentEvents = ref<Event[]>([])

// Sales ranking columns
const salesColumns: DataTableColumns<SalesRankingItem> = [
  {
    title: '排名',
    key: 'rank',
    width: 60,
    render: (_, index) => index + 1,
  },
  {
    title: '姓名',
    key: 'sale_name',
  },
  {
    title: '订单数',
    key: 'order_count',
    width: 80,
  },
  {
    title: '金额',
    key: 'total_amount',
    width: 120,
    render: (row) => formatAmount(row.total_amount),
  },
]

// Funnel computed
const funnelStages = computed(() => {
  if (!funnelData.value) return []
  const items = funnelData.value.funnel
  if (items.length === 0) return []
  const maxCount = Math.max(...items.map((s) => s.count), 1)
  const statusLabels: Record<string, string> = {
    potential: '潜在',
    following: '跟进',
    intention: '意向',
    signed: '签约',
    executing: '执行',
    completed: '已完成',
  }
  return items.map((item) => ({
    status: statusLabels[item.status] || item.status,
    count: item.count,
    percent: Math.round((item.count / maxCount) * 100),
  }))
})

// Supplier ranking columns
const supplierColumns: DataTableColumns<SupplierRankingItem> = [
  {
    title: '排名',
    key: 'rank',
    width: 60,
    render: (_, index) => index + 1,
  },
  {
    title: '名称',
    key: 'supplier_name',
  },
  {
    title: '类型',
    key: 'type',
    width: 80,
  },
  {
    title: '评分',
    key: 'rating',
    width: 80,
    render: (row) => row.rating.toFixed(1),
  },
  {
    title: '评价数',
    key: 'evaluation_count',
    width: 80,
  },
]

// Schedule heatmap computed
const currentMonth = computed(() => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
})

const heatmapGrid = computed(() => {
  if (!heatmapData.value) return { weeks: [] as { days: { date: string; count: number; dayOfMonth: number; isCurrentMonth: boolean }[] }[], totalMax: 0 }
  const month = heatmapData.value.month
  const [year, mon] = month.split('-').map(Number)
  const firstDay = new Date(year, mon - 1, 1)
  const lastDay = new Date(year, mon, 0)
  const startDow = firstDay.getDay() // 0=Sun
  const daysInMonth = lastDay.getDate()

  const countMap = new Map<string, number>()
  let maxCount = 0
  for (const item of heatmapData.value.heatmap) {
    countMap.set(item.date, item.count)
    if (item.count > maxCount) maxCount = item.count
  }

  const weeks: { days: { date: string; count: number; dayOfMonth: number; isCurrentMonth: boolean }[] }[] = []
  let currentWeek: { date: string; count: number; dayOfMonth: number; isCurrentMonth: boolean }[] = []

  // Pad start of first week
  for (let i = 0; i < startDow; i++) {
    currentWeek.push({ date: '', count: 0, dayOfMonth: 0, isCurrentMonth: false })
  }

  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${month}-${String(d).padStart(2, '0')}`
    const count = countMap.get(dateStr) || 0
    currentWeek.push({ date: dateStr, count, dayOfMonth: d, isCurrentMonth: true })
    if (currentWeek.length === 7) {
      weeks.push({ days: currentWeek })
      currentWeek = []
    }
  }
  // Pad remaining days of last week
  if (currentWeek.length > 0) {
    while (currentWeek.length < 7) {
      currentWeek.push({ date: '', count: 0, dayOfMonth: 0, isCurrentMonth: false })
    }
    weeks.push({ days: currentWeek })
  }

  return { weeks, totalMax: maxCount }
})

function getHeatmapColor(count: number, max: number): string {
  if (count === 0) return '#f5f5f5'
  const intensity = Math.ceil((count / Math.max(max, 1)) * 4)
  const colors = ['#c6e6c6', '#7dbd7d', '#3d9d3d', '#1a7a1a']
  return colors[Math.min(intensity, 4) - 1] || colors[3]
}

const weekDays = ['日', '一', '二', '三', '四', '五', '六']

// Payment method labels
const paymentMethodLabels: Record<string, string> = {
  bank_transfer: '银行转账',
  wechat: '微信支付',
  alipay: '支付宝',
  cash: '现金',
  card: '银行卡',
  other: '其他',
}

onMounted(async () => {
  const monthParam = currentMonth.value
  const results = await Promise.allSettled([
    getOverview(),
    getSalesRanking(),
    getConversionFunnel(),
    getFinanceSummary(),
    getScheduleHeatmap({ month: monthParam }),
    getSupplierRanking(),
    getEventList({ page_size: 5 }),
  ])

  const [overviewRes, salesRes, funnelRes, financeRes, heatmapRes, supplierRes, eventsRes] = results

  if (overviewRes.status === 'fulfilled') {
    overview.value = overviewRes.value
  }
  overviewLoading.value = false

  if (salesRes.status === 'fulfilled') {
    salesRanking.value = salesRes.value.ranking
  }
  salesLoading.value = false

  if (funnelRes.status === 'fulfilled') {
    funnelData.value = funnelRes.value
  }
  funnelLoading.value = false

  if (financeRes.status === 'fulfilled') {
    financeData.value = financeRes.value
  }
  financeLoading.value = false

  if (heatmapRes.status === 'fulfilled') {
    heatmapData.value = heatmapRes.value
  }
  heatmapLoading.value = false

  if (supplierRes.status === 'fulfilled') {
    supplierRanking.value = supplierRes.value.ranking
  }
  supplierLoading.value = false

  if (eventsRes.status === 'fulfilled') {
    recentEvents.value = eventsRes.value.items
  }
  eventsLoading.value = false
})
</script>

<template>
  <div>
    <!-- Top statistic cards -->
    <NGrid :x-gap="16" :y-gap="16" :cols="4">
      <NGi>
        <NCard>
          <NSkeleton v-if="overviewLoading" text :repeat="2" />
          <NStatistic v-else label="客户总数" :value="overview?.customers.total ?? 0">
            <template #suffix>人</template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NSkeleton v-if="overviewLoading" text :repeat="2" />
          <NStatistic v-else label="本月订单" :value="overview?.orders.count ?? 0">
            <template #suffix>单</template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NSkeleton v-if="overviewLoading" text :repeat="2" />
          <NStatistic v-else label="本月营收" :value="formatAmount(overview?.orders.total_amount ?? 0)" />
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NSkeleton v-if="overviewLoading" text :repeat="2" />
          <NStatistic v-else label="待执行活动" :value="overview?.upcoming_events ?? 0">
            <template #suffix>场</template>
          </NStatistic>
        </NCard>
      </NGi>
    </NGrid>

    <!-- Sales ranking + Conversion funnel -->
    <NGrid :x-gap="16" :y-gap="16" :cols="2" style="margin-top: 16px">
      <NGi>
        <NCard title="销售排行">
          <NSkeleton v-if="salesLoading" text :repeat="5" />
          <NDataTable
            v-else
            :columns="salesColumns"
            :data="salesRanking"
            :bordered="false"
            size="small"
            :pagination="false"
          />
        </NCard>
      </NGi>
      <NGi>
        <NCard title="转化漏斗">
          <NSkeleton v-if="funnelLoading" text :repeat="5" />
          <template v-else>
            <NSpace vertical :size="16">
              <div v-for="stage in funnelStages" :key="stage.status">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px">
                  <span style="font-size: 14px">{{ stage.status }}</span>
                  <span style="font-size: 14px; color: #999">{{ stage.count }} 人</span>
                </div>
                <NProgress
                  type="line"
                  :percentage="stage.percent"
                  :show-indicator="false"
                  :height="20"
                  :color="'#18a058'"
                  :rail-color="'#f0f0f0'"
                />
              </div>
              <div v-if="funnelStages.length === 0" style="text-align: center; color: #999; padding: 20px 0">
                暂无数据
              </div>
            </NSpace>
          </template>
        </NCard>
      </NGi>
    </NGrid>

    <!-- Finance summary + Schedule heatmap -->
    <NGrid :x-gap="16" :y-gap="16" :cols="2" style="margin-top: 16px">
      <NGi>
        <NCard title="财务汇总">
          <NSkeleton v-if="financeLoading" text :repeat="5" />
          <template v-else>
            <NSpace vertical :size="16">
              <NGrid :x-gap="12" :y-gap="12" :cols="3">
                <NGi>
                  <NStatistic label="总额" :value="formatAmount(financeData?.total_amount ?? 0)" />
                </NGi>
                <NGi>
                  <NStatistic label="已收" :value="formatAmount(financeData?.total_paid ?? 0)" />
                </NGi>
                <NGi>
                  <NStatistic label="应收" :value="formatAmount(financeData?.receivable ?? 0)" />
                </NGi>
              </NGrid>
              <div v-if="financeData?.payment_method_breakdown" style="margin-top: 8px">
                <div style="font-size: 13px; color: #666; margin-bottom: 8px">付款方式</div>
                <NSpace>
                  <NTag
                    v-for="(amount, method) in financeData.payment_method_breakdown"
                    :key="method"
                    type="info"
                    size="small"
                  >
                    {{ paymentMethodLabels[method] || method }}: {{ formatAmount(amount) }}
                  </NTag>
                </NSpace>
              </div>
            </NSpace>
          </template>
        </NCard>
      </NGi>
      <NGi>
        <NCard title="排期热力图">
          <template #header-extra>
            <span style="font-size: 13px; color: #999">{{ currentMonth }}</span>
          </template>
          <NSkeleton v-if="heatmapLoading" text :repeat="6" />
          <template v-else>
            <div style="overflow-x: auto">
              <!-- Week day headers -->
              <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; margin-bottom: 4px">
                <div
                  v-for="day in weekDays"
                  :key="day"
                  style="text-align: center; font-size: 12px; color: #999; padding: 2px 0"
                >
                  {{ day }}
                </div>
              </div>
              <!-- Calendar grid -->
              <div
                v-for="(week, wi) in heatmapGrid.weeks"
                :key="wi"
                style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; margin-bottom: 2px"
              >
                <div
                  v-for="(cell, di) in week.days"
                  :key="di"
                  :style="{
                    textAlign: 'center',
                    fontSize: '12px',
                    padding: '6px 2px',
                    borderRadius: '4px',
                    backgroundColor: cell.isCurrentMonth ? getHeatmapColor(cell.count, heatmapGrid.totalMax) : 'transparent',
                    color: cell.isCurrentMonth ? (cell.count > 0 ? '#fff' : '#666') : 'transparent',
                    cursor: 'default',
                    position: 'relative',
                  }"
                  :title="cell.isCurrentMonth ? `${cell.date}: ${cell.count} 场活动` : ''"
                >
                  {{ cell.dayOfMonth || '' }}
                </div>
              </div>
            </div>
          </template>
        </NCard>
      </NGi>
    </NGrid>

    <!-- Supplier ranking -->
    <NCard title="供应商排行" style="margin-top: 16px">
      <NSkeleton v-if="supplierLoading" text :repeat="5" />
      <NDataTable
        v-else
        :columns="supplierColumns"
        :data="supplierRanking"
        :bordered="false"
        size="small"
        :pagination="false"
      />
    </NCard>

    <!-- Recent events -->
    <NCard title="最近活动" style="margin-top: 16px">
      <NSkeleton v-if="eventsLoading" text :repeat="4" />
      <NList v-else>
        <NListItem v-for="event in recentEvents" :key="event.id">
          <NThing :title="event.title">
            <template #description>
              <NSpace size="small">
                <NTag size="small">{{ event.event_date }}</NTag>
                <NTag size="small" type="info">{{ event.status }}</NTag>
              </NSpace>
            </template>
          </NThing>
        </NListItem>
        <NListItem v-if="recentEvents.length === 0">
          <NThing title="暂无排期" />
        </NListItem>
      </NList>
    </NCard>
  </div>
</template>
