<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
import {
  NCard,
  NPageHeader,
  NButton,
  NSpace,
  NSelect,
  NDataTable,
  NTag,
  NSpin,
  NModal,
  NForm,
  NFormItem,
  NInputNumber,
  NInput,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns, FormInst, FormRules } from 'naive-ui'
import { getInvoices, createInvoice, updateInvoice, voidInvoice, uploadInvoicePdf } from '@/api/finance'
import type { Invoice, InvoiceType, InvoiceStatus, InvoiceCreateParams, PaginatedResult } from '@/api/finance'

const message = useMessage()

const loading = ref(false)
const data = ref<Invoice[]>([])
const showCreateModal = ref(false)
const showUpdateModal = ref(false)
const formRef = ref<FormInst | null>(null)
const submitting = ref(false)
const currentInvoice = ref<Invoice | null>(null)

const pagination = reactive({
  page: 1,
  pageSize: 15,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 15, 20, 50],
})

const filters = reactive({
  status: null as InvoiceStatus | null,
  invoice_type: null as InvoiceType | null,
})

const createForm = reactive<InvoiceCreateParams>({
  order_id: 0,
  invoice_type: 'normal',
  amount: 0,
  title: '',
  tax_no: '',
  note: '',
})

const updateForm = reactive({
  invoice_no: '',
  status: '' as InvoiceStatus | '',
})

const statusOptions = [
  { label: '待开票', value: 'pending' },
  { label: '开票中', value: 'processing' },
  { label: '已开票', value: 'issued' },
  { label: '已作废', value: 'voided' },
]

const typeOptions = [
  { label: '增值税普通发票', value: 'normal' },
  { label: '增值税专用发票', value: 'special' },
]

const createFormRules: FormRules = {
  order_id: [{ required: true, message: '请输入订单ID', type: 'number' }],
  invoice_type: [{ required: true, message: '请选择发票类型' }],
  amount: [{ required: true, message: '请输入开票金额', type: 'number' }],
  title: [{ required: true, message: '请输入发票抬头' }],
  tax_no: [{ required: true, message: '请输入纳税人识别号' }],
}

function getStatusTag(status: InvoiceStatus) {
  const map: Record<InvoiceStatus, { type: 'default' | 'info' | 'success' | 'warning' | 'error'; label: string }> = {
    pending: { type: 'info', label: '待开票' },
    processing: { type: 'warning', label: '开票中' },
    issued: { type: 'success', label: '已开票' },
    voided: { type: 'error', label: '已作废' },
  }
  return map[status] || { type: 'default' as const, label: status }
}

const columns: DataTableColumns<Invoice> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '订单ID', key: 'order_id', width: 80 },
  {
    title: '发票类型',
    key: 'invoice_type',
    width: 140,
    render(row) {
      return row.invoice_type === 'special' ? '增值税专用发票' : '增值税普通发票'
    },
  },
  {
    title: '金额',
    key: 'amount',
    width: 120,
    render(row) {
      return `¥${Number(row.amount).toLocaleString()}`
    },
  },
  {
    title: '抬头',
    key: 'title',
    width: 150,
    ellipsis: { tooltip: true },
  },
  {
    title: '发票号码',
    key: 'invoice_no',
    width: 140,
    render(row) {
      return row.invoice_no || '-'
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
    title: '操作',
    key: 'actions',
    width: 200,
    fixed: 'right',
    render(row) {
      const btns: any[] = []
      if (row.status === 'pending' || row.status === 'processing') {
        btns.push(
          h(NButton, { size: 'small', type: 'primary', text: true, onClick: () => openUpdateModal(row) }, { default: () => '处理' }),
        )
      }
      if (row.status === 'processing' || row.status === 'pending') {
        btns.push(
          h(NButton, { size: 'small', text: true, onClick: () => handleUploadPdf(row) }, { default: () => '上传PDF' }),
        )
      }
      if (row.status !== 'voided' && row.status !== 'issued') {
        btns.push(
          h(NButton, { size: 'small', type: 'error', text: true, onClick: () => handleVoid(row.id) }, { default: () => '作废' }),
        )
      }
      return h(NSpace, { size: 'small' }, { default: () => btns })
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
    if (filters.invoice_type) params.invoice_type = filters.invoice_type
    const res = (await getInvoices(params)) as unknown as PaginatedResult<Invoice>
    data.value = res.items
    pagination.itemCount = res.total
  } catch (err: any) {
    message.error(err.message || '获取开票列表失败')
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
  filters.status = null
  filters.invoice_type = null
  pagination.page = 1
  fetchData()
}

function openCreateModal() {
  createForm.order_id = 0
  createForm.invoice_type = 'normal'
  createForm.amount = 0
  createForm.title = ''
  createForm.tax_no = ''
  createForm.note = ''
  showCreateModal.value = true
}

function openUpdateModal(invoice: Invoice) {
  currentInvoice.value = invoice
  updateForm.invoice_no = invoice.invoice_no || ''
  updateForm.status = 'processing'
  showUpdateModal.value = true
}

async function handleCreate() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    const payload: any = { ...createForm }
    await createInvoice(payload)
    message.success('开票申请已提交')
    showCreateModal.value = false
    fetchData()
  } catch (err: any) {
    message.error(err.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function handleUpdate() {
  if (!currentInvoice.value) return
  submitting.value = true
  try {
    const data: any = {}
    if (updateForm.invoice_no) data.invoice_no = updateForm.invoice_no
    if (updateForm.status) data.status = updateForm.status
    data.issued_at = new Date().toISOString()
    await updateInvoice(currentInvoice.value.id, data)
    message.success('发票已更新')
    showUpdateModal.value = false
    fetchData()
  } catch (err: any) {
    message.error(err.message || '更新失败')
  } finally {
    submitting.value = false
  }
}

async function handleVoid(id: number) {
  try {
    await voidInvoice(id)
    message.success('发票已作废')
    fetchData()
  } catch (err: any) {
    message.error(err.message || '作废失败')
  }
}

function handleUploadPdf(invoice: Invoice) {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.pdf'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (!file) return
    try {
      await uploadInvoicePdf(invoice.id, file)
      message.success('PDF上传成功')
      fetchData()
    } catch (err: any) {
      message.error(err.message || '上传失败')
    }
  }
  input.click()
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div>
    <NPageHeader title="开票管理" subtitle="管理发票申请和开票记录">
      <template #extra>
        <NButton type="primary" @click="openCreateModal">申请开票</NButton>
      </template>
    </NPageHeader>

    <NCard style="margin-top: 16px">
      <NSpace vertical>
        <NSpace align="center" :wrap="true">
          <NSelect
            v-model:value="filters.status"
            placeholder="开票状态"
            :options="statusOptions"
            clearable
            style="width: 150px"
          />
          <NSelect
            v-model:value="filters.invoice_type"
            placeholder="发票类型"
            :options="typeOptions"
            clearable
            style="width: 170px"
          />
          <NButton type="primary" @click="handleSearch">查询</NButton>
          <NButton @click="handleReset">重置</NButton>
        </NSpace>

        <NSpin :show="loading">
          <NDataTable
            :columns="columns"
            :data="data"
            :row-key="(row: Invoice) => row.id"
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

    <!-- Create Modal -->
    <NModal v-model:show="showCreateModal" preset="card" title="申请开票" style="width: 550px">
      <NForm ref="formRef" :model="createForm" :rules="createFormRules" label-placement="left" label-width="120">
        <NFormItem label="订单ID" path="order_id">
          <NInputNumber v-model:value="createForm.order_id" placeholder="请输入订单ID" style="width: 100%" :show-button="false" />
        </NFormItem>
        <NFormItem label="发票类型" path="invoice_type">
          <NSelect v-model:value="createForm.invoice_type" :options="typeOptions" />
        </NFormItem>
        <NFormItem label="开票金额" path="amount">
          <NInputNumber v-model:value="createForm.amount" placeholder="请输入金额" :min="0.01" :precision="2" style="width: 100%" />
        </NFormItem>
        <NFormItem label="发票抬头" path="title">
          <NInput v-model:value="createForm.title" placeholder="请输入发票抬头" />
        </NFormItem>
        <NFormItem label="纳税人识别号" path="tax_no">
          <NInput v-model:value="createForm.tax_no" placeholder="请输入纳税人识别号" />
        </NFormItem>
        <NFormItem label="备注">
          <NInput v-model:value="createForm.note" type="textarea" placeholder="备注（可选）" :rows="2" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showCreateModal = false">取消</NButton>
          <NButton type="primary" :loading="submitting" @click="handleCreate">提交申请</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Update Modal -->
    <NModal v-model:show="showUpdateModal" preset="card" title="处理发票" style="width: 450px">
      <NForm label-placement="left" label-width="100">
        <NFormItem label="发票号码">
          <NInput v-model:value="updateForm.invoice_no" placeholder="请输入发票号码" />
        </NFormItem>
        <NFormItem label="状态">
          <NSelect v-model:value="updateForm.status" :options="statusOptions.filter(o => o.value !== 'voided')" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showUpdateModal = false">取消</NButton>
          <NButton type="primary" :loading="submitting" @click="handleUpdate">确认</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>
