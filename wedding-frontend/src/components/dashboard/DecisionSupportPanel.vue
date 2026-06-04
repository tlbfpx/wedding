<script setup lang="ts">
import { computed, h } from 'vue'
import { NCard, NSkeleton, NTabs, NTabPane, NDataTable, NProgress } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import type { DecisionSupportResponse } from '@/api/dashboard'

interface Props {
  loading?: boolean
  data?: DecisionSupportResponse
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
})

const sourceRoiColumns: DataTableColumns<DecisionSupportResponse['source_roi'][0]> = [
  {
    title: '来源',
    key: 'source',
  },
  {
    title: '获客数',
    key: 'lead_count',
    width: 80,
  },
  {
    title: '签约数',
    key: 'signed_count',
    width: 80,
  },
  {
    title: '转化率',
    key: 'conversion_rate',
    width: 80,
    render: (row) => `${(row.conversion_rate * 100).toFixed(0)}%`,
  },
  {
    title: '总营收',
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
    title: 'ROI',
    key: 'roi_score',
    width: 120,
    render: (row) => {
      const stars = '⭐'.repeat(row.roi_score)
      return stars || '-'
    },
  },
]

const serviceColumns: DataTableColumns<DecisionSupportResponse['service_breakdown'][0]> = [
  {
    title: '服务类型',
    key: 'service_type',
    width: 150,
  },
  {
    title: '收入占比',
    key: 'percent',
    width: 200,
    render: (row) => {
      return h('div', { style: 'display: flex; align-items: center; gap: 8px' }, [
        h(NProgress, {
          type: 'line',
          percentage: row.percent * 100,
          showIndicator: false,
          height: 16,
          railColor: '#f0f0f0',
        }),
        h('span', {
          style: 'width: 50px; text-align: right; font-size: 13px'
        }, `${(row.percent * 100).toFixed(0)}%`),
      ])
    },
  },
  {
    title: '营收',
    key: 'revenue',
    width: 100,
    render: (row) => `¥${(row.revenue / 10000).toFixed(1)}万`,
  },
  {
    title: '订单数',
    key: 'count',
    width: 80,
  },
]

const supplierColumns: DataTableColumns<DecisionSupportResponse['supplier_value'][0]> = [
  {
    title: '供应商',
    key: 'supplier_name',
  },
  {
    title: '类型',
    key: 'type',
    width: 80,
  },
  {
    title: '合作次数',
    key: 'cooperation_count',
    width: 100,
  },
  {
    title: '总金额',
    key: 'total_amount',
    width: 100,
    render: (row) => `¥${(row.total_amount / 10000).toFixed(1)}万`,
  },
  {
    title: '平均评分',
    key: 'avg_rating',
    width: 100,
    render: (row) => row.avg_rating.toFixed(1),
  },
  {
    title: '性价比',
    key: 'value_score',
    width: 120,
    render: (row) => {
      const stars = '⭐'.repeat(row.value_score)
      return stars || '-'
    },
  },
]

const serviceTypeLabels: Record<string, string> = {
  planning: '策划执行',
  photo: '摄影摄像',
  hosting: '主持服务',
  floral: '花艺布置',
  makeup: '化妆造型',
  other: '其他服务',
}

const servicesWithLabels = computed(() => {
  if (!props.data?.service_breakdown) return []
  return props.data.service_breakdown.map(s => ({
    ...s,
    service_type: serviceTypeLabels[s.service_type] || s.service_type,
  }))
})
</script>

<template>
  <NCard title="决策支撑">
    <NSkeleton v-if="loading" text :repeat="10" />
    <NTabs v-else type="line" animated>
      <NTabPane name="source" tab="客户来源 ROI">
        <NDataTable
          :columns="sourceRoiColumns"
          :data="data?.source_roi || []"
          :bordered="false"
          size="small"
          :pagination="false"
          :scroll-x="800"
        />
      </NTabPane>
      <NTabPane name="service" tab="服务类型收入">
        <NDataTable
          :columns="serviceColumns"
          :data="servicesWithLabels"
          :bordered="false"
          size="small"
          :pagination="false"
          :scroll-x="600"
        />
      </NTabPane>
      <NTabPane name="supplier" tab="供应商性价比">
        <NDataTable
          :columns="supplierColumns"
          :data="data?.supplier_value || []"
          :bordered="false"
          size="small"
          :pagination="{
            pageSize: 10,
          }"
          :scroll-x="800"
        />
      </NTabPane>
    </NTabs>
  </NCard>
</template>
