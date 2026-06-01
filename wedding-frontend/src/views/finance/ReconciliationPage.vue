<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import {
  NCard,
  NPageHeader,
  NButton,
  NSpace,
  NSelect,
  NDataTable,
  NSpin,
  NStatistic,
  NDescriptions,
  NDescriptionsItem,
  NModal,
  NInput,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { getReconciliationReport, confirmReconciliation, getReconciliationHistory } from '@/api/finance'
import type { ReconciliationRecord, PaginatedResult } from '@/api/finance'

const message = useMessage()

const loading = ref(false)
const historyLoading = ref(false)
const report = ref<any>(null)
const historyData = ref<ReconciliationRecord[]>([])
const showConfirmModal = ref(false)
const confirmNotes = ref('')
const confirming = ref(false)

const selectedPeriod = ref('')

const pagination = reactive({
  page: 1,
  pageSize: 10,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
})

function getPeriodOptions() {
  const options: { label: string; value: string }[] = []
  const now = new Date()
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    options.push({ label: `${d.getFullYear()}年${d.getMonth() + 1}月`, value })
  }
  return options
}

const periodOptions = getPeriodOptions()

const historyColumns: DataTableColumns<ReconciliationRecord> = [
  {
    title: '对账周期',
    key: 'period',
    width: 120,
  },
  {
    title: '确认人',
    key: 'confirmed_by',
    width: 100,
    render(row) {
      return row.confirmed_by ? String(row.confirmed_by) : '-'
    },
  },
  {
    title: '确认时间',
    key: 'confirmed_at',
    width: 180,
    render(row) {
      return row.confirmed_at ? new Date(row.confirmed_at).toLocaleString('zh-CN') : '-'
    },
  },
  {
    title: '备注',
    key: 'notes',
    width: 200,
    ellipsis: { tooltip: true },
    render(row) {
      return row.notes || '-'
    },
  },
]

async function generateReport() {
  if (!selectedPeriod.value) {
    message.warning('请选择对账周期')
    return
  }
  loading.value = true
  try {
    report.value = await getReconciliationReport(selectedPeriod.value) as unknown as any
  } catch (err: any) {
    message.error(err.message || '生成对账报表失败')
  } finally {
    loading.value = false
  }
}

async function fetchHistory() {
  historyLoading.value = true
  try {
    const res = (await getReconciliationHistory({
      page: pagination.page,
      page_size: pagination.pageSize,
    })) as unknown as PaginatedResult<ReconciliationRecord>
    historyData.value = res.items
    pagination.itemCount = res.total
  } catch (err: any) {
    message.error(err.message || '获取对账历史失败')
  } finally {
    historyLoading.value = false
  }
}

function openConfirmModal() {
  confirmNotes.value = ''
  showConfirmModal.value = true
}

async function handleConfirm() {
  if (!selectedPeriod.value) return
  confirming.value = true
  try {
    await confirmReconciliation({
      period: selectedPeriod.value,
      notes: confirmNotes.value || undefined,
    })
    message.success('对账确认成功')
    showConfirmModal.value = false
    fetchHistory()
  } catch (err: any) {
    message.error(err.message || '确认失败')
  } finally {
    confirming.value = false
  }
}

function handleHistoryPageChange(page: number) {
  pagination.page = page
  fetchHistory()
}

function handleHistoryPageSizeChange(pageSize: number) {
  pagination.pageSize = pageSize
  pagination.page = 1
  fetchHistory()
}

onMounted(() => {
  fetchHistory()
})
</script>

<template>
  <div>
    <NPageHeader title="财务对账" subtitle="按月核对收支数据" />

    <NCard style="margin-top: 16px">
      <NSpace vertical :size="16">
        <NSpace align="center" :wrap="true">
          <NSelect
            v-model:value="selectedPeriod"
            placeholder="选择对账周期"
            :options="periodOptions"
            style="width: 200px"
          />
          <NButton type="primary" :loading="loading" @click="generateReport">生成报表</NButton>
          <NButton v-if="report" @click="openConfirmModal">确认对账</NButton>
        </NSpace>

        <NSpin :show="loading">
          <template v-if="report">
            <NDescriptions bordered :column="2" label-placement="left">
              <NDescriptionsItem label="应收总额">
                ¥{{ Number(report.income_expected || report.receivable_total || 0).toLocaleString() }}
              </NDescriptionsItem>
              <NDescriptionsItem label="实收总额">
                ¥{{ Number(report.income_actual || report.received_total || 0).toLocaleString() }}
              </NDescriptionsItem>
              <NDescriptionsItem label="应付总额">
                ¥{{ Number(report.expense_expected || report.payable_total || 0).toLocaleString() }}
              </NDescriptionsItem>
              <NDescriptionsItem label="实付总额">
                ¥{{ Number(report.expense_actual || report.paid_total || 0).toLocaleString() }}
              </NDescriptionsItem>
              <NDescriptionsItem label="收入差异">
                ¥{{ Number(report.income_diff || 0).toLocaleString() }}
              </NDescriptionsItem>
              <NDescriptionsItem label="支出差异">
                ¥{{ Number(report.expense_diff || 0).toLocaleString() }}
              </NDescriptionsItem>
            </NDescriptions>
          </template>
          <NCard v-else-if="!loading" style="text-align: center; padding: 40px; color: #999">
            请选择对账周期并点击"生成报表"
          </NCard>
        </NSpin>
      </NSpace>
    </NCard>

    <NCard title="对账历史" style="margin-top: 16px">
      <NSpin :show="historyLoading">
        <NDataTable
          :columns="historyColumns"
          :data="historyData"
          :row-key="(row: ReconciliationRecord) => row.id"
          :pagination="{
            page: pagination.page,
            pageSize: pagination.pageSize,
            itemCount: pagination.itemCount,
            showSizePicker: pagination.showSizePicker,
            pageSizes: pagination.pageSizes,
            onPageChange: handleHistoryPageChange,
            onPageSizeChange: handleHistoryPageSizeChange,
          }"
          striped
        />
      </NSpin>
    </NCard>

    <NModal v-model:show="showConfirmModal" preset="card" title="确认对账" style="width: 450px">
      <NInput
        v-model:value="confirmNotes"
        type="textarea"
        placeholder="备注（可选）"
        :rows="3"
      />
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showConfirmModal = false">取消</NButton>
          <NButton type="primary" :loading="confirming" @click="handleConfirm">确认</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>
