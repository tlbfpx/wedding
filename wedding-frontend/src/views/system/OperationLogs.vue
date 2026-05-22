<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
import {
  NPageHeader,
  NCard,
  NSpace,
  NDataTable,
  NSelect,
  NDatePicker,
  NTag,
  useMessage,
  type DataTableColumns,
  type SelectOption,
} from 'naive-ui'
import { getOperationLogs, getUsers } from '@/api/users'
import type { OperationLog, User } from '@/api/users'

const message = useMessage()

const loading = ref(false)
const logs = ref<OperationLog[]>([])
const total = ref(0)
const pagination = reactive({
  page: 1,
  pageSize: 20,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
})

// User options for filter
const userOptions = ref<SelectOption[]>([])

// Filters
const filters = reactive({
  user_id: null as number | null,
  module: null as string | null,
  action: null as string | null,
  dateRange: null as [number, number] | null,
})

const moduleOptions: SelectOption[] = [
  { label: '客户管理', value: 'customer' },
  { label: '排期管理', value: 'event' },
  { label: '订单管理', value: 'order' },
  { label: '供应商管理', value: 'supplier' },
  { label: '场地管理', value: 'venue' },
  { label: '审批管理', value: 'approval' },
  { label: '系统管理', value: 'system' },
]

const actionOptions: SelectOption[] = [
  { label: '创建', value: 'create' },
  { label: '更新', value: 'update' },
  { label: '删除', value: 'delete' },
  { label: '查看', value: 'read' },
  { label: '导出', value: 'export' },
  { label: '登录', value: 'login' },
]

const actionColorMap: Record<string, string> = {
  create: 'success',
  update: 'info',
  delete: 'error',
  read: 'default',
  export: 'warning',
  login: 'info',
}

const actionLabelMap: Record<string, string> = {
  create: '创建',
  update: '更新',
  delete: '删除',
  read: '查看',
  export: '导出',
  login: '登录',
}

const columns: DataTableColumns<OperationLog> = [
  {
    title: '时间',
    key: 'created_at',
    width: 180,
    sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    defaultSortOrder: 'descend',
  },
  { title: '操作人', key: 'user_name', width: 100 },
  {
    title: '模块',
    key: 'module',
    width: 120,
    render(row) {
      const mod = moduleOptions.find((m) => m.value === row.module)
      return mod ? mod.label : row.module
    },
  },
  {
    title: '操作',
    key: 'action',
    width: 90,
    render(row) {
      return h(NTag, { size: 'small', type: actionColorMap[row.action] as any }, {
        default: () => actionLabelMap[row.action] || row.action,
      })
    },
  },
  {
    title: '对象',
    key: 'detail',
    ellipsis: { tooltip: true },
    render(row) {
      if (row.detail) return row.detail
      if (row.target) return row.target
      return '-'
    },
  },
  { title: 'IP', key: 'ip', width: 130 },
]

async function fetchLogs() {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (filters.user_id) params.user_id = filters.user_id
    if (filters.module) params.module = filters.module
    if (filters.action) params.action = filters.action
    if (filters.dateRange) {
      const [start, end] = filters.dateRange
      params.date_start = new Date(start).toISOString().slice(0, 10)
      params.date_end = new Date(end).toISOString().slice(0, 10)
    }
    const res = await getOperationLogs(params)
    logs.value = res.items
    total.value = res.total
  } catch (err: any) {
    message.error(err.message || '获取操作日志失败')
  } finally {
    loading.value = false
  }
}

async function fetchUserOptions() {
  try {
    const res = await getUsers({ page_size: 100 })
    userOptions.value = res.items.map((u: User) => ({ label: u.name, value: u.id }))
  } catch {
    // Silently handle
  }
}

function handlePageChange(page: number) {
  pagination.page = page
  fetchLogs()
}

function handlePageSizeChange(pageSize: number) {
  pagination.pageSize = pageSize
  pagination.page = 1
  fetchLogs()
}

function handleSearch() {
  pagination.page = 1
  fetchLogs()
}

function handleDateRangeChange(val: [number, number] | null) {
  filters.dateRange = val
  handleSearch()
}

function handleFilterChange() {
  handleSearch()
}

onMounted(() => {
  fetchLogs()
  fetchUserOptions()
})
</script>

<template>
  <div>
    <NPageHeader title="操作日志" />

    <NCard style="margin-top: 16px;">
      <NSpace align="center" style="margin-bottom: 16px;" :wrap="true">
        <NSelect
          v-model:value="filters.user_id"
          :options="userOptions"
          placeholder="操作人"
          clearable
          style="width: 150px;"
          @update:value="handleFilterChange"
        />
        <NSelect
          v-model:value="filters.module"
          :options="moduleOptions"
          placeholder="模块"
          clearable
          style="width: 140px;"
          @update:value="handleFilterChange"
        />
        <NSelect
          v-model:value="filters.action"
          :options="actionOptions"
          placeholder="操作类型"
          clearable
          style="width: 130px;"
          @update:value="handleFilterChange"
        />
        <NDatePicker
          type="daterange"
          clearable
          style="width: 280px;"
          @update:value="handleDateRangeChange"
        />
      </NSpace>

      <NDataTable
        :columns="columns"
        :data="logs"
        :loading="loading"
        :bordered="false"
        :pagination="{
          page: pagination.page,
          pageSize: pagination.pageSize,
          itemCount: total,
          showSizePicker: pagination.showSizePicker,
          pageSizes: pagination.pageSizes,
          onPageChange: handlePageChange,
          onPageSizeChange: handlePageSizeChange,
        }"
        :row-key="(row: OperationLog) => row.id"
      />
    </NCard>
  </div>
</template>
