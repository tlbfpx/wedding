<script setup lang="ts">
import { ref, reactive, h, onMounted, computed } from 'vue'
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
  NModal,
  NTag,
  NPopconfirm,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import {
  getCustomers,
  recycleCustomer,
  transferCustomer,
} from '@/api/customers'
import type { Customer, CustomerListParams } from '@/api/customers'
import { getUsers } from '@/api/users'
import type { User } from '@/api/users'
import CustomerForm from './CustomerForm.vue'

const router = useRouter()
const message = useMessage()

// --- State ---
const loading = ref(false)
const customers = ref<Customer[]>([])
const total = ref(0)
const pagination = reactive({
  page: 1,
  pageSize: 10,
})
const filters = reactive({
  keyword: '',
  status: null as string | null,
  source: null as string | null,
  dateRange: null as [number, number] | null,
})

// Form modal
const formVisible = ref(false)
const editingCustomerId = ref<number | null>(null)

// Transfer modal
const transferVisible = ref(false)
const transferCustomerId = ref<number | null>(null)
const transferTargetUserId = ref<number | null>(null)
const salesUsers = ref<User[]>([])
const transferLoading = ref(false)

// --- Filter options ---
const statusOptions = [
  { label: '潜在客户', value: 'potential' },
  { label: '跟进中', value: 'following' },
  { label: '有意向', value: 'intention' },
  { label: '已签约', value: 'signed' },
  { label: '已流失', value: 'lost' },
]

const sourceOptions = [
  { label: '线上咨询', value: 'online' },
  { label: '电话咨询', value: 'phone' },
  { label: '到店咨询', value: 'visit' },
  { label: '朋友推荐', value: 'referral' },
  { label: '婚礼展会', value: 'exhibition' },
  { label: '其他', value: 'other' },
]

// --- Helpers ---
const statusMap: Record<string, { label: string; type: 'default' | 'info' | 'warning' | 'success' | 'error' }> = {
  potential: { label: '潜在客户', type: 'default' },
  following: { label: '跟进中', type: 'info' },
  intention: { label: '有意向', type: 'warning' },
  signed: { label: '已签约', type: 'success' },
  lost: { label: '已流失', type: 'error' },
}

const sourceLabelMap: Record<string, string> = {
  online: '线上咨询',
  phone: '电话咨询',
  visit: '到店咨询',
  referral: '朋友推荐',
  exhibition: '婚礼展会',
  other: '其他',
}

function getStatusTag(status: string) {
  const info = statusMap[status] || { label: status, type: 'default' as const }
  return h(NTag, { type: info.type, size: 'small' }, { default: () => info.label })
}

function formatBudget(budget?: number | null) {
  if (!budget) return '-'
  return `¥${budget.toLocaleString()}`
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
    width: 100,
  },
  {
    title: '手机',
    key: 'phone',
    width: 130,
  },
  {
    title: '来源',
    key: 'source',
    width: 100,
    render: (row) => sourceLabelMap[row.source || ''] || row.source || '-',
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => getStatusTag(row.status),
  },
  {
    title: '预算',
    key: 'budget',
    width: 110,
    render: (row) => formatBudget(row.budget),
  },
  {
    title: '婚期',
    key: 'wedding_date',
    width: 110,
    render: (row) => formatDate(row.wedding_date),
  },
  {
    title: '负责销售',
    key: 'assigned_user',
    width: 100,
    render: (row) => row.assigned_user?.name || '-',
  },
  {
    title: '最近跟进',
    key: 'updated_at',
    width: 110,
    render: (row) => formatDate(row.updated_at),
  },
  {
    title: '操作',
    key: 'actions',
    width: 260,
    fixed: 'right',
    render: (row) =>
      h(NSpace, { size: 'small' }, () => [
        h(
          NButton,
          { size: 'small', type: 'primary', text: true, onClick: () => handleView(row) },
          { default: () => '查看' }
        ),
        h(
          NButton,
          { size: 'small', type: 'info', text: true, onClick: () => handleEdit(row) },
          { default: () => '编辑' }
        ),
        h(
          NButton,
          { size: 'small', type: 'warning', text: true, onClick: () => handleTransfer(row) },
          { default: () => '转移' }
        ),
        h(
          NPopconfirm,
          { onPositiveClick: () => handleRecycle(row) },
          {
            trigger: () =>
              h(
                NButton,
                { size: 'small', type: 'error', text: true },
                { default: () => '回收' }
              ),
            default: () => '确认将该客户回收到公海池？',
          }
        ),
      ]),
  },
])

// --- Data fetching ---
async function fetchCustomers() {
  loading.value = true
  try {
    const params: CustomerListParams = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.status) params.status = filters.status
    if (filters.source) params.source = filters.source

    const res = await getCustomers(params)
    customers.value = res.items
    total.value = res.total
  } catch (err: any) {
    message.error(err.message || '获取客户列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchSalesUsers() {
  try {
    const res = await getUsers({ page: 1, page_size: 100 })
    salesUsers.value = res.items
  } catch {
    // silently ignore
  }
}

// --- Event handlers ---
function handleView(row: Customer) {
  router.push(`/customers/${row.id}`)
}

function handleEdit(row: Customer) {
  editingCustomerId.value = row.id
  formVisible.value = true
}

function handleCreate() {
  editingCustomerId.value = null
  formVisible.value = true
}

function handleTransfer(row: Customer) {
  transferCustomerId.value = row.id
  transferTargetUserId.value = null
  transferVisible.value = true
  fetchSalesUsers()
}

async function confirmTransfer() {
  if (!transferCustomerId.value || !transferTargetUserId.value) {
    message.warning('请选择目标销售人员')
    return
  }
  transferLoading.value = true
  try {
    await transferCustomer(transferCustomerId.value, transferTargetUserId.value)
    message.success('客户转移成功')
    transferVisible.value = false
    await fetchCustomers()
  } catch (err: any) {
    message.error(err.message || '转移失败')
  } finally {
    transferLoading.value = false
  }
}

async function handleRecycle(row: Customer) {
  try {
    await recycleCustomer(row.id)
    message.success('客户已回收到公海池')
    await fetchCustomers()
  } catch (err: any) {
    message.error(err.message || '回收失败')
  }
}

function handleSearch() {
  pagination.page = 1
  fetchCustomers()
}

function handleReset() {
  filters.keyword = ''
  filters.status = null
  filters.source = null
  filters.dateRange = null
  pagination.page = 1
  fetchCustomers()
}

function handlePageChange(page: number) {
  pagination.page = page
  fetchCustomers()
}

function handlePageSizeChange(pageSize: number) {
  pagination.pageSize = pageSize
  pagination.page = 1
  fetchCustomers()
}

function handleFormSuccess() {
  fetchCustomers()
}

// --- Lifecycle ---
onMounted(() => {
  fetchCustomers()
})
</script>

<template>
  <div>
    <NPageHeader title="客户管理">
      <template #extra>
        <NButton type="primary" @click="handleCreate">新增客户</NButton>
      </template>
    </NPageHeader>

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
          v-model:value="filters.status"
          :options="statusOptions"
          placeholder="客户状态"
          clearable
          style="width: 140px"
        />
        <NSelect
          v-model:value="filters.source"
          :options="sourceOptions"
          placeholder="客户来源"
          clearable
          style="width: 140px"
        />
        <NDatePicker
          v-model:value="filters.dateRange"
          type="daterange"
          clearable
          style="width: 280px"
        />
        <NButton type="primary" @click="handleSearch">搜索</NButton>
        <NButton @click="handleReset">重置</NButton>
      </NSpace>

      <!-- Data table -->
      <NDataTable
        :columns="columns"
        :data="customers"
        :loading="loading"
        :row-key="(row: Customer) => row.id"
        :scroll-x="1200"
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

    <!-- Create / Edit modal -->
    <CustomerForm
      v-model:visible="formVisible"
      :customer-id="editingCustomerId"
      @success="handleFormSuccess"
    />

    <!-- Transfer modal -->
    <NModal
      v-model:show="transferVisible"
      preset="card"
      title="转移客户"
      style="width: 420px"
    >
      <NSpace vertical>
        <p>选择目标销售人员：</p>
        <NSelect
          v-model:value="transferTargetUserId"
          :options="salesUsers.map((u) => ({ label: u.name, value: u.id }))"
          placeholder="请选择销售人员"
          filterable
        />
      </NSpace>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="transferVisible = false">取消</NButton>
          <NButton
            type="primary"
            :loading="transferLoading"
            :disabled="!transferTargetUserId"
            @click="confirmTransfer"
          >
            确认转移
          </NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>
