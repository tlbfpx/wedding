<script setup lang="ts">
import { ref, reactive, onMounted, h, computed } from 'vue'
import {
  NCard,
  NPageHeader,
  NButton,
  NSpace,
  NSelect,
  NDatePicker,
  NDataTable,
  NTag,
  NSpin,
  NModal,
  NForm,
  NFormItem,
  NInputNumber,
  NInput,
  NStatistic,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns, FormInst, FormRules } from 'naive-ui'
import { getTransactions, createExpense, getTransactionSummary } from '@/api/finance'
import type { Transaction, TransactionType, ExpenseCategory, ExpenseCreateParams, TransactionSummary, PaginatedResult } from '@/api/finance'

const message = useMessage()

const loading = ref(false)
const data = ref<Transaction[]>([])
const summary = ref<TransactionSummary | null>(null)
const showModal = ref(false)
const formRef = ref<FormInst | null>(null)
const submitting = ref(false)

const pagination = reactive({
  page: 1,
  pageSize: 15,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 15, 20, 50],
})

const filters = reactive({
  type: null as TransactionType | null,
  category: null as ExpenseCategory | null,
  dateRange: null as [number, number] | null,
})

const formData = reactive<ExpenseCreateParams>({
  category: 'other',
  amount: 0,
  order_id: undefined,
  supplier_id: undefined,
  date: '',
  note: '',
})

const typeOptions = [
  { label: '收入', value: 'income' },
  { label: '支出', value: 'expense' },
]

const categoryOptions = [
  { label: '供应商付款', value: 'supplier_payment' },
  { label: '人工费用', value: 'labor' },
  { label: '场地费用', value: 'venue' },
  { label: '物料费用', value: 'material' },
  { label: '其他', value: 'other' },
]

const formRules: FormRules = {
  category: [{ required: true, message: '请选择支出分类' }],
  amount: [{ required: true, message: '请输入金额', type: 'number' }],
}

const netColor = computed(() => {
  if (!summary.value) return '#333'
  const net = Number(summary.value.net_amount)
  return net >= 0 ? '#18a058' : '#d03050'
})

const columns: DataTableColumns<Transaction> = [
  { title: 'ID', key: 'id', width: 60 },
  {
    title: '类型',
    key: 'type',
    width: 80,
    render(row) {
      const isIncome = row.type === 'income'
      return h(NTag, { type: isIncome ? 'success' : 'warning', size: 'small' }, { default: () => isIncome ? '收入' : '支出' })
    },
  },
  {
    title: '分类',
    key: 'category',
    width: 120,
    render(row) {
      const map: Record<string, string> = {
        supplier_payment: '供应商付款', labor: '人工费用', venue: '场地费用',
        material: '物料费用', other: '其他', refund: '退款',
      }
      return row.category ? (map[row.category] || row.category) : '-'
    },
  },
  {
    title: '金额',
    key: 'amount',
    width: 120,
    render(row) {
      const prefix = row.type === 'income' ? '+' : '-'
      return `${prefix}¥${Number(row.amount).toLocaleString()}`
    },
  },
  {
    title: '关联订单',
    key: 'order_id',
    width: 100,
    render(row) {
      return row.order_id ? String(row.order_id) : '-'
    },
  },
  {
    title: '日期',
    key: 'date',
    width: 120,
    render(row) {
      return row.date || '-'
    },
  },
  {
    title: '备注',
    key: 'note',
    width: 150,
    ellipsis: { tooltip: true },
    render(row) {
      return row.note || '-'
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
    if (filters.type) params.type = filters.type
    if (filters.category) params.category = filters.category
    if (filters.dateRange) {
      params.date_start = new Date(filters.dateRange[0]).toISOString().slice(0, 10)
      params.date_end = new Date(filters.dateRange[1]).toISOString().slice(0, 10)
    }
    const res = (await getTransactions(params)) as unknown as PaginatedResult<Transaction>
    data.value = res.items
    pagination.itemCount = res.total
  } catch (err: any) {
    message.error(err.message || '获取收支明细失败')
  } finally {
    loading.value = false
  }
}

async function fetchSummary() {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10)
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10)
  try {
    summary.value = await getTransactionSummary(start, end) as unknown as TransactionSummary
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
  filters.type = null
  filters.category = null
  filters.dateRange = null
  pagination.page = 1
  fetchData()
}

function openCreateModal() {
  formData.category = 'other'
  formData.amount = 0
  formData.order_id = undefined
  formData.supplier_id = undefined
  formData.date = ''
  formData.note = ''
  showModal.value = true
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    const payload: any = {
      category: formData.category,
      amount: formData.amount,
    }
    if (formData.order_id) payload.order_id = formData.order_id
    if (formData.supplier_id) payload.supplier_id = formData.supplier_id
    if (formData.date) payload.date = formData.date
    if (formData.note) payload.note = formData.note
    await createExpense(payload)
    message.success('支出登记成功')
    showModal.value = false
    fetchData()
    fetchSummary()
  } catch (err: any) {
    message.error(err.message || '登记失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchData()
  fetchSummary()
})
</script>

<template>
  <div>
    <NPageHeader title="收支明细" subtitle="查看所有收入和支出记录">
      <template #extra>
        <NButton type="primary" @click="openCreateModal">登记支出</NButton>
      </template>
    </NPageHeader>

    <NSpace :size="16" style="margin-top: 16px" :wrap="true" v-if="summary">
      <NCard style="min-width: 180px">
        <NStatistic label="本月收入" :value="Number(summary.income_total).toLocaleString()">
          <template #prefix>¥</template>
        </NStatistic>
      </NCard>
      <NCard style="min-width: 180px">
        <NStatistic label="本月支出" :value="Number(summary.expense_total).toLocaleString()">
          <template #prefix>¥</template>
        </NStatistic>
      </NCard>
      <NCard style="min-width: 180px">
        <NStatistic label="本月净额" :value="Number(summary.net_amount).toLocaleString()">
          <template #prefix>¥</template>
          <template #default="{ value }">
            <span :style="{ color: netColor }">{{ value }}</span>
          </template>
        </NStatistic>
      </NCard>
    </NSpace>

    <NCard style="margin-top: 16px">
      <NSpace vertical>
        <NSpace align="center" :wrap="true">
          <NSelect
            v-model:value="filters.type"
            placeholder="收支类型"
            :options="typeOptions"
            clearable
            style="width: 130px"
          />
          <NSelect
            v-model:value="filters.category"
            placeholder="支出分类"
            :options="categoryOptions"
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
            :row-key="(row: Transaction) => row.id"
            :pagination="{
              page: pagination.page,
              pageSize: pagination.pageSize,
              itemCount: pagination.itemCount,
              showSizePicker: pagination.showSizePicker,
              pageSizes: pagination.pageSizes,
              onPageChange: handlePageChange,
              onPageSizeChange: handlePageSizeChange,
            }"
            :scroll-x="1050"
            striped
          />
        </NSpin>
      </NSpace>
    </NCard>

    <NModal v-model:show="showModal" preset="card" title="登记支出" style="width: 500px">
      <NForm ref="formRef" :model="formData" :rules="formRules" label-placement="left" label-width="100">
        <NFormItem label="支出分类" path="category">
          <NSelect v-model:value="formData.category" :options="categoryOptions" />
        </NFormItem>
        <NFormItem label="金额" path="amount">
          <NInputNumber v-model:value="formData.amount" placeholder="请输入金额" :min="0.01" :precision="2" style="width: 100%" />
        </NFormItem>
        <NFormItem label="关联订单">
          <NInputNumber v-model:value="formData.order_id" placeholder="订单ID（可选）" style="width: 100%" :show-button="false" />
        </NFormItem>
        <NFormItem label="关联供应商">
          <NInputNumber v-model:value="formData.supplier_id" placeholder="供应商ID（可选）" style="width: 100%" :show-button="false" />
        </NFormItem>
        <NFormItem label="日期">
          <NInput v-model:value="formData.date" placeholder="YYYY-MM-DD（可选）" />
        </NFormItem>
        <NFormItem label="备注">
          <NInput v-model:value="formData.note" type="textarea" placeholder="备注（可选）" :rows="2" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showModal = false">取消</NButton>
          <NButton type="primary" :loading="submitting" @click="handleSubmit">确认登记</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>
