<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
import {
  NCard,
  NPageHeader,
  NButton,
  NSpace,
  NInput,
  NSelect,
  NDatePicker,
  NDataTable,
  NTag,
  NSpin,
  NStatistic,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { getReceivables, getOverdueReceivables } from '@/api/finance'
import type { Receivable, ReceivableStatus, PaginatedResult } from '@/api/finance'

const message = useMessage()

const loading = ref(false)
const data = ref<Receivable[]>([])
const overdueList = ref<Receivable[]>([])
const overdueCount = ref(0)

const pagination = reactive({
  page: 1,
  pageSize: 15,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 15, 20, 50],
})

const filters = reactive({
  status: null as ReceivableStatus | null,
  dateRange: null as [number, number] | null,
  keyword: '',
})

const statusOptions = [
  { label: '未收款', value: 'unpaid' },
  { label: '部分收款', value: 'partial' },
  { label: '已收款', value: 'paid' },
  { label: '已逾期', value: 'overdue' },
]

function getStatusTag(status: ReceivableStatus) {
  const map: Record<ReceivableStatus, { type: 'default' | 'info' | 'success' | 'warning' | 'error'; label: string }> = {
    unpaid: { type: 'info', label: '未收款' },
    partial: { type: 'warning', label: '部分收款' },
    paid: { type: 'success', label: '已收款' },
    overdue: { type: 'error', label: '已逾期' },
  }
  return map[status] || { type: 'default' as const, label: status }
}

const columns: DataTableColumns<Receivable> = [
  { title: '订单ID', key: 'order_id', width: 80 },
  {
    title: '应收金额',
    key: 'total_amount',
    width: 120,
    render(row) {
      return `¥${Number(row.total_amount).toLocaleString()}`
    },
  },
  {
    title: '已收金额',
    key: 'received_amount',
    width: 120,
    render(row) {
      return `¥${Number(row.received_amount).toLocaleString()}`
    },
  },
  {
    title: '剩余金额',
    key: 'remaining_amount',
    width: 120,
    render(row) {
      return `¥${Number(row.remaining_amount).toLocaleString()}`
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render(row) {
      const { type, label } = getStatusTag(row.status)
      return h(NTag, { type, size: 'small' }, { default: () => label })
    },
  },
  {
    title: '到期日',
    key: 'due_date',
    width: 120,
    render(row) {
      return row.due_date || '-'
    },
  },
  {
    title: '逾期天数',
    key: 'overdue_days',
    width: 100,
    render(row) {
      if (row.is_overdue && row.overdue_days > 0) {
        return h(NTag, { type: 'error', size: 'small' }, { default: () => `${row.overdue_days}天` })
      }
      return '-'
    },
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 180,
    render(row) {
      return row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-'
    },
  },
]

async function fetchData() {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (filters.status) params.status = filters.status
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.dateRange) {
      params.date_start = new Date(filters.dateRange[0]).toISOString().slice(0, 10)
      params.date_end = new Date(filters.dateRange[1]).toISOString().slice(0, 10)
    }
    const res = (await getReceivables(params)) as unknown as PaginatedResult<Receivable>
    data.value = res.items
    pagination.itemCount = res.total
  } catch (err: any) {
    message.error(err.message || '获取应收列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchOverdue() {
  try {
    const res = (await getOverdueReceivables({ page: 1, page_size: 100 })) as unknown as PaginatedResult<Receivable>
    overdueList.value = res.items
    overdueCount.value = res.total
  } catch {
    // non-critical
  }
}

function handlePageChange(page: number) {
  pagination.page = page
  fetchData()
}

function handlePageSizeChange(pageSize: number) {
  pagination.pageSize = pageSize
  pagination.page = 1
  fetchData()
}

function handleSearch() {
  pagination.page = 1
  fetchData()
}

function handleReset() {
  filters.status = null
  filters.dateRange = null
  filters.keyword = ''
  pagination.page = 1
  fetchData()
}

onMounted(() => {
  fetchData()
  fetchOverdue()
})
</script>

<template>
  <div>
    <NPageHeader title="应收账款" subtitle="跟踪订单应收及收款状态" />

    <NSpace :size="16" style="margin-top: 16px" :wrap="true">
      <NCard style="flex: 1; min-width: 200px">
        <NStatistic label="逾期应收" :value="overdueCount">
          <template #suffix>条</template>
        </NStatistic>
      </NCard>
    </NSpace>

    <NCard style="margin-top: 16px">
      <NSpace vertical>
        <NSpace align="center" :wrap="true">
          <NInput
            v-model:value="filters.keyword"
            placeholder="客户名/订单号"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          />
          <NSelect
            v-model:value="filters.status"
            placeholder="收款状态"
            :options="statusOptions"
            clearable
            style="width: 150px"
          />
          <NDatePicker
            v-model:value="filters.dateRange"
            type="daterange"
            clearable
            style="width: 280px"
          />
          <NButton type="primary" @click="handleSearch">查询</NButton>
          <NButton @click="handleReset">重置</NButton>
        </NSpace>

        <NSpin :show="loading">
          <NDataTable
            :columns="columns"
            :data="data"
            :row-key="(row: Receivable) => row.id"
            :pagination="{
              page: pagination.page,
              pageSize: pagination.pageSize,
              itemCount: pagination.itemCount,
              showSizePicker: pagination.showSizePicker,
              pageSizes: pagination.pageSizes,
              onPageChange: handlePageChange,
              onPageSizeChange: handlePageSizeChange,
            }"
            :scroll-x="1000"
            striped
          />
        </NSpin>
      </NSpace>
    </NCard>
  </div>
</template>
