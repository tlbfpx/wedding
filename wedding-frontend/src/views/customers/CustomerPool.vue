<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import {
  NCard,
  NPageHeader,
  NButton,
  NSpace,
  NInput,
  NSelect,
  NDataTable,
  NPopconfirm,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { getCustomerPool, claimCustomer } from '@/api/customers'
import type { Customer, CustomerListParams } from '@/api/customers'

const message = useMessage()

// --- State ---
const loading = ref(false)
const poolCustomers = ref<Customer[]>([])
const total = ref(0)
const pagination = reactive({
  page: 1,
  pageSize: 10,
})
const filters = reactive({
  keyword: '',
  source: null as string | null,
  recycledDays: null as number | null,
})

// --- Filter options ---
const sourceOptions = [
  { label: '线上咨询', value: 'online' },
  { label: '电话咨询', value: 'phone' },
  { label: '到店咨询', value: 'visit' },
  { label: '朋友推荐', value: 'referral' },
  { label: '婚礼展会', value: 'exhibition' },
  { label: '其他', value: 'other' },
]

const recycledDaysOptions = [
  { label: '3天内', value: 3 },
  { label: '7天内', value: 7 },
  { label: '15天内', value: 15 },
  { label: '30天内', value: 30 },
]

const sourceLabelMap: Record<string, string> = {
  online: '线上咨询',
  phone: '电话咨询',
  visit: '到店咨询',
  referral: '朋友推荐',
  exhibition: '婚礼展会',
  other: '其他',
}

function formatDate(dateStr?: string | null) {
  if (!dateStr) return '-'
  return dateStr.split('T')[0]
}

// --- Table columns ---
const columns = computed<DataTableColumns<Customer>>(() => [
  {
    title: '姓名',
    key: 'name',
    width: 120,
  },
  {
    title: '手机',
    key: 'phone',
    width: 140,
  },
  {
    title: '来源',
    key: 'source',
    width: 120,
    render: (row) => sourceLabelMap[row.source || ''] || row.source || '-',
  },
  {
    title: '回收时间',
    key: 'updated_at',
    width: 140,
    render: (row) => formatDate(row.updated_at),
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    fixed: 'right',
    render: (row) =>
      h(
        NPopconfirm,
        { onPositiveClick: () => handleClaim(row) },
        {
          trigger: () =>
            h(
              NButton,
              { size: 'small', type: 'primary' },
              { default: () => '认领' }
            ),
          default: () => '确认认领该客户？',
        }
      ),
  },
])

// Need to import h for render functions
import { h } from 'vue'

// --- Data fetching ---
async function fetchPool() {
  loading.value = true
  try {
    const params: CustomerListParams = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.source) params.source = filters.source

    const res = await getCustomerPool(params)
    poolCustomers.value = res.items
    total.value = res.total
  } catch (err: any) {
    message.error(err.message || '获取公海池列表失败')
  } finally {
    loading.value = false
  }
}

// --- Event handlers ---
async function handleClaim(row: Customer) {
  try {
    await claimCustomer(row.id)
    message.success('认领成功')
    await fetchPool()
  } catch (err: any) {
    message.error(err.message || '认领失败')
  }
}

function handleSearch() {
  pagination.page = 1
  fetchPool()
}

function handleReset() {
  filters.keyword = ''
  filters.source = null
  filters.recycledDays = null
  pagination.page = 1
  fetchPool()
}

function handlePageChange(page: number) {
  pagination.page = page
  fetchPool()
}

function handlePageSizeChange(pageSize: number) {
  pagination.pageSize = pageSize
  pagination.page = 1
  fetchPool()
}

// --- Lifecycle ---
onMounted(() => {
  fetchPool()
})
</script>

<template>
  <div>
    <NPageHeader title="公海池" />

    <NCard style="margin-top: 16px">
      <!-- Filter bar -->
      <NSpace :size="12" align="center" style="margin-bottom: 16px" :wrap="true">
        <NInput
          v-model:value="filters.keyword"
          placeholder="搜索姓名/手机号"
          clearable
          style="width: 200px"
          @keyup.enter="handleSearch"
        />
        <NSelect
          v-model:value="filters.source"
          :options="sourceOptions"
          placeholder="客户来源"
          clearable
          style="width: 140px"
        />
        <NSelect
          v-model:value="filters.recycledDays"
          :options="recycledDaysOptions"
          placeholder="回收时间"
          clearable
          style="width: 140px"
        />
        <NButton type="primary" @click="handleSearch">搜索</NButton>
        <NButton @click="handleReset">重置</NButton>
      </NSpace>

      <!-- Data table -->
      <NDataTable
        :columns="columns"
        :data="poolCustomers"
        :loading="loading"
        :row-key="(row: Customer) => row.id"
        :scroll-x="620"
        remote
        :pagination="{
          page: pagination.page,
          pageSize: pagination.pageSize,
          itemCount: total,
          pageSizes: [10, 20, 50],
          showSizePicker: true,
        }"
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
    </NCard>
  </div>
</template>
