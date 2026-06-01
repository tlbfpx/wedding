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
import { getRefunds, createRefund, updateRefundStatus } from '@/api/finance'
import type { Refund, RefundStatus, RefundCreateParams, PaginatedResult } from '@/api/finance'

const message = useMessage()

const loading = ref(false)
const data = ref<Refund[]>([])
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
  status: null as RefundStatus | null,
  order_id: undefined as number | undefined,
})

const formData = reactive<RefundCreateParams>({
  order_id: 0,
  amount: 0,
  reason: '',
  note: '',
})

const statusOptions = [
  { label: '待审批', value: 'pending_approval' },
  { label: '已批准', value: 'approved' },
  { label: '已拒绝', value: 'rejected' },
  { label: '已退款', value: 'refunded' },
]

const formRules: FormRules = {
  order_id: [{ required: true, message: '请输入订单ID', type: 'number' }],
  amount: [{ required: true, message: '请输入退款金额', type: 'number' }],
  reason: [{ required: true, message: '请输入退款原因' }],
}

function getStatusTag(status: RefundStatus) {
  const map: Record<RefundStatus, { type: 'default' | 'info' | 'success' | 'warning' | 'error'; label: string }> = {
    pending_approval: { type: 'warning', label: '待审批' },
    approved: { type: 'success', label: '已批准' },
    rejected: { type: 'error', label: '已拒绝' },
    refunded: { type: 'info', label: '已退款' },
  }
  return map[status] || { type: 'default' as const, label: status }
}

const columns: DataTableColumns<Refund> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '订单ID', key: 'order_id', width: 80 },
  {
    title: '退款金额',
    key: 'amount',
    width: 120,
    render(row) {
      return `¥${Number(row.amount).toLocaleString()}`
    },
  },
  {
    title: '退款原因',
    key: 'reason',
    width: 180,
    ellipsis: { tooltip: true },
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
      return row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-'
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    fixed: 'right',
    render(row) {
      if (row.status === 'approved') {
        return h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            text: true,
            onClick: () => handleMarkRefunded(row.id),
          },
          { default: () => '标记已退款' },
        )
      }
      return '-'
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
    if (filters.order_id) params.order_id = filters.order_id
    const res = (await getRefunds(params)) as unknown as PaginatedResult<Refund>
    data.value = res.items
    pagination.itemCount = res.total
  } catch (err: any) {
    message.error(err.message || '获取退款列表失败')
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
  filters.order_id = undefined
  pagination.page = 1
  fetchData()
}

function openCreateModal() {
  formData.order_id = 0
  formData.amount = 0
  formData.reason = ''
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
      reason: formData.reason,
    }
    if (formData.note) payload.note = formData.note
    await createRefund(payload)
    message.success('退款申请已提交')
    showModal.value = false
    fetchData()
  } catch (err: any) {
    message.error(err.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function handleMarkRefunded(id: number) {
  try {
    await updateRefundStatus(id, 'refunded')
    message.success('已标记为退款完成')
    fetchData()
  } catch (err: any) {
    message.error(err.message || '操作失败')
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div>
    <NPageHeader title="退款管理" subtitle="管理退款申请和退款记录">
      <template #extra>
        <NButton type="primary" @click="openCreateModal">申请退款</NButton>
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
            v-model:value="filters.status"
            placeholder="退款状态"
            :options="statusOptions"
            clearable
            style="width: 150px"
          />
          <NButton type="primary" @click="handleSearch">查询</NButton>
          <NButton @click="handleReset">重置</NButton>
        </NSpace>

        <NSpin :show="loading">
          <NDataTable
            :columns="columns"
            :data="data"
            :row-key="(row: Refund) => row.id"
            :pagination="{
              page: pagination.page,
              pageSize: pagination.pageSize,
              itemCount: pagination.itemCount,
              showSizePicker: pagination.showSizePicker,
              pageSizes: pagination.pageSizes,
              onPageChange: handlePageChange,
              onPageSizeChange: handlePageSizeChange,
            }"
            :scroll-x="900"
            striped
          />
        </NSpin>
      </NSpace>
    </NCard>

    <NModal v-model:show="showModal" preset="card" title="申请退款" style="width: 500px">
      <NForm ref="formRef" :model="formData" :rules="formRules" label-placement="left" label-width="100">
        <NFormItem label="订单ID" path="order_id">
          <NInputNumber v-model:value="formData.order_id" placeholder="请输入订单ID" style="width: 100%" :show-button="false" />
        </NFormItem>
        <NFormItem label="退款金额" path="amount">
          <NInputNumber v-model:value="formData.amount" placeholder="请输入退款金额" :min="0.01" :precision="2" style="width: 100%" />
        </NFormItem>
        <NFormItem label="退款原因" path="reason">
          <NInput v-model:value="formData.reason" type="textarea" placeholder="请输入退款原因" :rows="3" />
        </NFormItem>
        <NFormItem label="备注">
          <NInput v-model:value="formData.note" type="textarea" placeholder="备注（可选）" :rows="2" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showModal = false">取消</NButton>
          <NButton type="primary" :loading="submitting" @click="handleSubmit">提交申请</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>
