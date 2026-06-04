<script setup lang="ts">
import { computed, ref } from 'vue'
import { NCard, NSkeleton, NGrid, NGi, NStatistic, NSpace, NProgress, NDataTable, NSelect } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import type { TeamEfficiencyResponse } from '@/api/dashboard'

interface Props {
  loading?: boolean
  data?: TeamEfficiencyResponse
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
})

const sortBy = ref<string>('revenue')

const stageLabels: Record<string, string> = {
  potential: '潜在',
  following: '跟进',
  intention: '意向',
  signed: '签约',
  lost: '流失',
}

const funnelStages = computed(() => {
  if (!props.data?.funnel) return []
  return props.data.funnel.map(item => ({
    label: stageLabels[item.stage] || item.stage,
    count: item.count,
    rate: item.rate,
    percent: item.rate * 100,
  }))
})

const maxFunnelCount = computed(() => {
  const counts = props.data?.funnel?.map(f => f.count) || []
  return Math.max(...counts, 1)
})

const salesRanking = computed(() => {
  if (!props.data?.ranking) return []
  return [...props.data.ranking].sort((a, b) => {
    switch (sortBy.value) {
      case 'revenue':
        return b.revenue - a.revenue
      case 'order_count':
        return b.order_count - a.order_count
      case 'conversion_rate':
        return b.conversion_rate - a.conversion_rate
      default:
        return b.revenue - a.revenue
    }
  })
})

const sortOptions = [
  { label: '按营收', value: 'revenue' },
  { label: '按订单数', value: 'order_count' },
  { label: '按转化率', value: 'conversion_rate' },
]

const columns: DataTableColumns<TeamEfficiencyResponse['ranking'][0]> = [
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
    title: '团队',
    key: 'team',
    width: 100,
  },
  {
    title: '订单数',
    key: 'order_count',
    width: 80,
  },
  {
    title: '营收',
    key: 'revenue',
    width: 100,
    render: (row) => `¥${(row.revenue / 10000).toFixed(1)}万`,
  },
  {
    title: '客单价',
    key: 'avg_order_value',
    width: 80,
    render: (row) => `¥${(row.avg_order_value / 10000).toFixed(2)}万`,
  },
  {
    title: '转化率',
    key: 'conversion_rate',
    width: 80,
    render: (row) => `${(row.conversion_rate * 100).toFixed(0)}%`,
  },
  {
    title: '跟进数',
    key: 'follow_up_count',
    width: 80,
  },
]

function formatAmount(amount: number): string {
  return '¥' + amount.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}
</script>

<template>
  <NCard title="团队效能">
    <template #header-extra>
      <NSelect v-if="data?.ranking" v-model:value="sortBy" :options="sortOptions" size="small" style="width: 100px" />
    </template>
    <NSkeleton v-if="loading" text :repeat="10" />
    <template v-else>
      <!-- 团队对比 + 转化漏斗 -->
      <NGrid :x-gap="24" :y-gap="16" :cols="2" style="margin-bottom: 24px">
        <NGi>
          <div style="font-size: 14px; font-weight: 500; margin-bottom: 12px">团队对比</div>
          <NSpace v-if="data?.teams && data.teams.length > 0" vertical :size="12">
            <div v-for="team in data.teams" :key="team.team" style="display: flex; align-items: center; gap: 8px">
              <div style="width: 80px; font-size: 13px">{{ team.team }}</div>
              <NProgress
                type="line"
                :percentage="(team.avg_revenue / Math.max(...data.teams!.map(t => t.avg_revenue))) * 100"
                :show-indicator="false"
                :height="16"
                :rail-color="'#f0f0f0'"
              />
              <div style="width: 80px; text-align: right; font-size: 13px; color: #666">
                {{ formatAmount(team.avg_revenue) }}/人
              </div>
            </div>
          </NSpace>
          <div v-else style="text-align: center; color: #999; padding: 20px 0; font-size: 13px">
            暂无团队数据
          </div>
        </NGi>
        <NGi>
          <div style="font-size: 14px; font-weight: 500; margin-bottom: 12px">转化漏斗</div>
          <NSpace vertical :size="8">
            <div v-for="stage in funnelStages" :key="stage.label" style="display: flex; align-items: center; gap: 8px">
              <div style="width: 60px; font-size: 13px">{{ stage.label }}</div>
              <NProgress
                type="line"
                :percentage="stage.percent"
                :show-indicator="false"
                :height="16"
                :rail-color="'#f0f0f0'"
                :color="stage.label === '流失' ? '#d03050' : '#18a058'"
              />
              <div style="width: 60px; text-align: right; font-size: 13px; color: #666">
                {{ stage.count }}
              </div>
            </div>
          </NSpace>
        </NGi>
      </NGrid>

      <!-- 销售排行榜 -->
      <div style="margin-top: 16px">
        <NDataTable
          :columns="columns"
          :data="salesRanking"
          :bordered="false"
          size="small"
          :pagination="{
            pageSize: 5,
            pageSizeOptions: [5, 10, 20],
          }"
        />
      </div>
    </template>
  </NCard>
</template>
