<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
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
  useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { getOrders } from '@/api/orders'
import type { Order, PaginatedResult } from '@/api/orders'
import { exportReport } from '@/api/reports'

const router = useRouter()
const message = useMessage()

const loading = ref(false)
const data = ref<Order[]>([])
const pagination = reactive({
  page: 1,
  pageSize: 15,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 15, 20, 50],
})

const filters = reactive({
  keyword: '',
  status: null as string | null,
  dateRange: null as [number, number] | null,
})

const statusOptions = [
  { label: '意向', value: 'intention' },
  { label: '已签约', value: 'signed' },
  { label: '执行中', value: 'executing' },
  { label: '已完成', value: 'completed' },
  { label: '已取消', value: 'cancelled' },
]

function getStatusTag(status: string) {
  const map: Record<string, { type: 'default' | 'info' | 'success' | 'warning' | 'error'; label: string }> = {
    intention: { type: 'info', label: '意向' },
    signed: { type: 'success', label: '已签约' },
    executing: { type: 'warning', label: '执行中' },
    completed: { type: 'default', label: '已完成' },
    cancelled: { type: 'error', label: '已取消' },
  }
  return map[status] || { type: 'default' as const, label: status }
}

const columns: DataTableColumns<Order> = [
  {
    title: '订单号',
    key: 'order_no',
    width: 160,
  },
  {
    title: '客户名',
    key: 'customer',
    width: 120,
    render(row) {
      return row.customer?.name || '-'
    },
  },
  {
    title: '销售',
    key: 'sale',
    width: 100,
    render(row) {
      return (row as any).sale?.name || '-'
    },
  },
  {
    title: '策划',
    key: 'planner',
    width: 100,
    render(row) {
      return (row as any).planner?.name || '-'
    },
  },
  {
    title: '总金额',
    key: 'total_amount',
    width: 120,
    render(row) {
      return `¥${row.total_amount.toLocaleString()}`
    },
  },
  {
    title: '已收',
    key: 'paid_amount',
    width: 120,
    render(row) {
      return `¥${row.paid_amount.toLocaleString()}`
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
    title: '创建时间',
    key: 'created_at',
    width: 180,
    render(row) {
      return new Date(row.created_at).toLocaleString('zh-CN')
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    fixed: 'right',
    render(row) {
      return h(
        NButton,
        {
          size: 'small',
          type: 'primary',
          text: true,
          onClick: () => router.push(`/orders/${row.id}`),
        },
        { default: () => '查看' },
      )
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
    if (filters.keyword) {
      params.keyword = filters.keyword
    }
    if (filters.status) {
      params.status = filters.status
    }
    if (filters.dateRange) {
      params.date_start = new Date(filters.dateRange[0]).toISOString().slice(0, 10)
      params.date_end = new Date(filters.dateRange[1]).toISOString().slice(0, 10)
    }
    const res = (await getOrders(params)) as unknown as PaginatedResult<Order>
    data.value = res.items
    pagination.itemCount = res.total
  } catch (err: any) {
    message.error(err.message || '获取订单列表失败')
  } finally {
    loading.value = false
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
  filters.keyword = ''
  filters.status = null
  filters.dateRange = null
  pagination.page = 1
  fetchData()
}

function handleCreate() {
  router.push('/orders/create')
}

async function handleExport() {
  try {
    const params: any = { report_type: 'order' }
    if (filters.status) params.status = filters.status
    if (filters.dateRange) {
      params.date_start = new Date(filters.dateRange[0]).toISOString().slice(0, 10)
      params.date_end = new Date(filters.dateRange[1]).toISOString().slice(0, 10)
    }
    const blob = await exportReport(params)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `订单报表_${new Date().toISOString().slice(0, 10)}.xlsx`
    link.click()
    window.URL.revokeObjectURL(url)
    message.success('导出成功')
  } catch (e: any) {
    message.error(e.message || '导出失败')
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div>
    <NPageHeader title="订单管理" subtitle="管理所有订单信息">
      <template #extra>
        <NSpace>
          <NButton @click="handleExport">导出</NButton>
          <NButton type="primary" @click="handleCreate">新建订单</NButton>
        </NSpace>
      </template>
    </NPageHeader>

    <NCard style="margin-top: 16px">
      <NSpace vertical>
        <NSpace align="center" :wrap="true">
          <NInput
            v-model:value="filters.keyword"
            placeholder="订单号/客户名"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          />
          <NSelect
            v-model:value="filters.status"
            placeholder="订单状态"
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
            :row-key="(row: Order) => row.id"
            :pagination="{
              page: pagination.page,
              pageSize: pagination.pageSize,
              itemCount: pagination.itemCount,
              showSizePicker: pagination.showSizePicker,
              pageSizes: pagination.pageSizes,
              onPageChange: handlePageChange,
              onPageSizeChange: handlePageSizeChange,
            }"
            :scroll-x="1200"
            striped
          />
        </NSpin>
      </NSpace>
    </NCard>
  </div>
</template>
