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
  NModal,
  NForm,
  NFormItem,
  NInputNumber,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns, FormInst, FormRules } from 'naive-ui'
import { getPayments, createPayment, deletePayment } from '@/api/finance'
import type { FinancePayment, PaymentMethod, PaymentCreateParams, PaginatedResult } from '@/api/finance'

const message = useMessage()

const loading = ref(false)
const data = ref<FinancePayment[]>([])
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
  order_id: null as number | null,
  method: null as PaymentMethod | null,
  dateRange: null as [number, number] | null,
})

const formData = reactive<PaymentCreateParams>({
  order_id: 0,
  amount: 0,
  method: 'transfer',
  paid_at: '',
  note: '',
})

const methodOptions = [
  { label: '现金', value: 'cash' },
  { label: '转账', value: 'transfer' },
  { label: '微信', value: 'wechat' },
  { label: '支付宝', value: 'alipay' },
  { label: '刷卡', value: 'card' },
]

const formRules: FormRules = {
  order_id: [{ required: true, message: '请输入订单ID', type: 'number' }],
  amount: [{ required: true, message: '请输入金额', type: 'number' }],
  method: [{ required: true, message: '请选择付款方式' }],
}

function getMethodLabel(method: string) {
  const map: Record<string, string> = {
    cash: '现金', transfer: '转账', wechat: '微信', alipay: '支付宝', card: '刷卡',
  }
  return map[method] || method
}

const columns: DataTableColumns<FinancePayment> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '订单ID', key: 'order_id', width: 80 },
  {
    title: '金额',
    key: 'amount',
    width: 120,
    render(row) {
      return `¥${Number(row.amount).toLocaleString()}`
    },
  },
  {
    title: '付款方式',
    key: 'method',
    width: 100,
    render(row) {
      return h(NTag, { size: 'small', type: 'info' }, { default: () => getMethodLabel(row.method) })
    },
  },
  {
    title: '收款日期',
    key: 'paid_at',
    width: 180,
    render(row) {
      return row.paid_at ? new Date(row.paid_at).toLocaleString('zh-CN') : '-'
    },
  },
  {
    title: '备注',
    key: 'note',
    width: 150,
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
  {
    title: '操作',
    key: 'actions',
    width: 80,
    fixed: 'right',
    render(row) {
      return h(
        NButton,
        {
          size: 'small',
          type: 'error',
          text: true,
          onClick: () => handleDelete(row.id),
        },
        { default: () => '删除' },
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
    if (filters.order_id) params.order_id = filters.order_id
    if (filters.method) params.method = filters.method
    if (filters.dateRange) {
      params.date_start = new Date(filters.dateRange[0]).toISOString().slice(0, 10)
      params.date_end = new Date(filters.dateRange[1]).toISOString().slice(0, 10)
    }
    const res = (await getPayments(params)) as unknown as PaginatedResult<FinancePayment>
    data.value = res.items
    pagination.itemCount = res.total
  } catch (err: any) {
    message.error(err.message || '获取收款列表失败')
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
  filters.order_id = null
  filters.method = null
  filters.dateRange = null
  pagination.page = 1
  fetchData()
}

function openCreateModal() {
  formData.order_id = 0
  formData.amount = 0
  formData.method = 'transfer'
  formData.paid_at = ''
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
      order_id: formData.order_id,
      amount: formData.amount,
      method: formData.method,
    }
    if (formData.paid_at) payload.paid_at = formData.paid_at
    if (formData.note) payload.note = formData.note
    await createPayment(payload)
    message.success('收款登记成功')
    showModal.value = false
    fetchData()
  } catch (err: any) {
    message.error(err.message || '登记失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(id: number) {
  try {
    await deletePayment(id)
    message.success('已删除')
    fetchData()
  } catch (err: any) {
    message.error(err.message || '删除失败')
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div>
    <NPageHeader title="收款管理" subtitle="登记和查询收款记录">
      <template #extra>
        <NButton type="primary" @click="openCreateModal">收款登记</NButton>
      </template>
    </NPageHeader>

    <NCard style="margin-top: 16px">
      <NSpace vertical>
        <NSpace align="center" :wrap="true">
          <NInputNumber
            v-model:value="filters.order_id"
            placeholder="订单ID"
            clearable
            style="width: 150px"
            :show-button="false"
          />
          <NSelect
            v-model:value="filters.method"
            placeholder="付款方式"
            :options="methodOptions"
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
            :row-key="(row: FinancePayment) => row.id"
            :pagination="{
              page: pagination.page,
              pageSize: pagination.pageSize,
              itemCount: pagination.itemCount,
              showSizePicker: pagination.showSizePicker,
              pageSizes: pagination.pageSizes,
              onPageChange: handlePageChange,
              onPageSizeChange: handlePageSizeChange,
            }"
            :scroll-x="1100"
            striped
          />
        </NSpin>
      </NSpace>
    </NCard>

    <NModal v-model:show="showModal" preset="card" title="收款登记" style="width: 500px">
      <NForm ref="formRef" :model="formData" :rules="formRules" label-placement="left" label-width="100">
        <NFormItem label="订单ID" path="order_id">
          <NInputNumber v-model:value="formData.order_id" placeholder="请输入订单ID" style="width: 100%" :show-button="false" />
        </NFormItem>
        <NFormItem label="金额" path="amount">
          <NInputNumber v-model:value="formData.amount" placeholder="请输入收款金额" :min="0.01" :precision="2" style="width: 100%" />
        </NFormItem>
        <NFormItem label="付款方式" path="method">
          <NSelect v-model:value="formData.method" :options="methodOptions" />
        </NFormItem>
        <NFormItem label="收款日期" path="paid_at">
          <NInput v-model:value="formData.paid_at" placeholder="YYYY-MM-DD（可选）" />
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
