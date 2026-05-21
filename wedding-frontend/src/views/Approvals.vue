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
  NModal,
  NInput,
  NSpin,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { getApprovals, approveApproval, rejectApproval } from '@/api/orders'
import type { Approval, PaginatedResult } from '@/api/orders'

const message = useMessage()

const loading = ref(false)
const data = ref<Approval[]>([])
const pagination = reactive({
  page: 1,
  pageSize: 15,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 15, 20, 50],
})

const filters = reactive({
  status: null as string | null,
  type: null as string | null,
})

const statusFilterOptions = [
  { label: '待审批', value: 'pending' },
  { label: '已通过', value: 'approved' },
  { label: '已驳回', value: 'rejected' },
]

const typeFilterOptions = [
  { label: '折扣审批', value: 'discount' },
  { label: '退款审批', value: 'refund' },
  { label: '取消审批', value: 'cancel' },
]

function getStatusTag(status: string) {
  const map: Record<string, { type: 'default' | 'info' | 'success' | 'warning' | 'error'; label: string }> = {
    pending: { type: 'warning', label: '待审批' },
    approved: { type: 'success', label: '已通过' },
    rejected: { type: 'error', label: '已驳回' },
  }
  return map[status] || { type: 'default' as const, label: status }
}

function getTypeLabel(type: string) {
  const map: Record<string, string> = {
    discount: '折扣审批',
    refund: '退款审批',
    cancel: '取消审批',
  }
  return map[type] || type
}

const actionModalVisible = ref(false)
const actionType = ref<'approve' | 'reject'>('approve')
const actionRemark = ref('')
const actionTargetId = ref<number | null>(null)
const actionSubmitting = ref(false)

const columns: DataTableColumns<Approval> = [
  {
    title: '类型',
    key: 'type',
    width: 120,
    render(row) {
      return getTypeLabel(row.type)
    },
  },
  {
    title: '关联订单',
    key: 'order_no',
    width: 160,
    render(row) {
      return row.order_no || '-'
    },
  },
  {
    title: '申请人',
    key: 'applicant',
    width: 100,
    render(row) {
      return row.applicant?.name || '-'
    },
  },
  {
    title: '理由',
    key: 'reason',
    width: 200,
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
    title: '审批人',
    key: 'approver',
    width: 100,
    render(row) {
      return row.approver?.name || '-'
    },
  },
  {
    title: '审批备注',
    key: 'approver_remark',
    width: 150,
    ellipsis: { tooltip: true },
    render(row) {
      return row.approver_remark || '-'
    },
  },
  {
    title: '申请时间',
    key: 'created_at',
    width: 180,
    render(row) {
      return new Date(row.created_at).toLocaleString('zh-CN')
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    fixed: 'right',
    render(row) {
      if (row.status !== 'pending') return '-'
      return h(NSpace, { size: 'small' }, () => [
        h(
          NButton,
          {
            size: 'small',
            type: 'success',
            onClick: () => openActionModal(row.id, 'approve'),
          },
          { default: () => '通过' },
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'error',
            onClick: () => openActionModal(row.id, 'reject'),
          },
          { default: () => '驳回' },
        ),
      ])
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
    if (filters.status) {
      params.status = filters.status
    }
    if (filters.type) {
      params.type = filters.type
    }
    const res = (await getApprovals(params)) as unknown as PaginatedResult<Approval>
    data.value = res.items
    pagination.itemCount = res.total
  } catch (err: any) {
    message.error(err.message || '获取审批列表失败')
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
  filters.type = null
  pagination.page = 1
  fetchData()
}

function openActionModal(id: number, type: 'approve' | 'reject') {
  actionTargetId.value = id
  actionType.value = type
  actionRemark.value = ''
  actionModalVisible.value = true
}

async function handleAction() {
  if (!actionTargetId.value) return
  actionSubmitting.value = true
  try {
    const payload = { note: actionRemark.value || undefined }
    if (actionType.value === 'approve') {
      await approveApproval(actionTargetId.value, payload)
      message.success('审批通过')
    } else {
      await rejectApproval(actionTargetId.value, payload)
      message.success('已驳回')
    }
    actionModalVisible.value = false
    await fetchData()
  } catch (err: any) {
    message.error(err.message || '操作失败')
  } finally {
    actionSubmitting.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div>
    <NPageHeader title="审批管理" subtitle="管理所有审批申请" />

    <NCard style="margin-top: 16px">
      <NSpace vertical>
        <NSpace align="center" :wrap="true">
          <NSelect
            v-model:value="filters.status"
            placeholder="审批状态"
            :options="statusFilterOptions"
            clearable
            style="width: 150px"
          />
          <NSelect
            v-model:value="filters.type"
            placeholder="审批类型"
            :options="typeFilterOptions"
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
            :row-key="(row: Approval) => row.id"
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

    <!-- 审批操作弹窗 -->
    <NModal
      v-model:show="actionModalVisible"
      preset="dialog"
      :title="actionType === 'approve' ? '通过审批' : '驳回审批'"
      :positive-text="actionType === 'approve' ? '确认通过' : '确认驳回'"
      :type="actionType === 'approve' ? 'success' : 'warning'"
      negative-text="取消"
      :loading="actionSubmitting"
      @positive-click="handleAction"
    >
      <NInput
        v-model:value="actionRemark"
        type="textarea"
        :placeholder="actionType === 'approve' ? '审批备注（可选）' : '请填写驳回原因'"
        :rows="3"
      />
    </NModal>
  </div>
</template>
