<script setup lang="ts">
import { ref, onMounted, h, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NCard,
  NPageHeader,
  NButton,
  NSpace,
  NDescriptions,
  NDescriptionsItem,
  NDataTable,
  NTag,
  NModal,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NSelect,
  NDatePicker,
  NUpload,
  NDivider,
  NSpin,
  NPopconfirm,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns, UploadFileInfo } from 'naive-ui'
import {
  getOrder,
  updateOrderStatus,
  addPayment,
  uploadContract,
  getQuotePdf,
  createApproval,
} from '@/api/orders'
import type { Order, OrderItem, Payment } from '@/api/orders'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const loading = ref(true)
const order = ref<Order | null>(null)
const orderId = Number(route.params.id)

const paymentModalVisible = ref(false)
const cancelModalVisible = ref(false)
const cancelReason = ref('')
const submitting = ref(false)

const paymentForm = ref({
  amount: null as number | null,
  method: null as string | null,
  paid_at: null as number | null,
  remark: '',
})

const methodOptions = [
  { label: '现金', value: 'cash' },
  { label: '银行卡', value: 'bank_transfer' },
  { label: '微信', value: 'wechat' },
  { label: '支付宝', value: 'alipay' },
  { label: '其他', value: 'other' },
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

const canSign = computed(() => order.value?.status === 'intention')
const canExecute = computed(() => order.value?.status === 'signed')
const canComplete = computed(() => order.value?.status === 'executing')
const canCancel = computed(() => {
  if (!order.value) return false
  return ['signed', 'executing'].includes(order.value.status)
})

const itemColumns: DataTableColumns<OrderItem> = [
  { title: '类型', key: 'type', width: 100 },
  { title: '名称', key: 'name', width: 150 },
  { title: '数量', key: 'quantity', width: 80 },
  {
    title: '单价',
    key: 'unit_price',
    width: 100,
    render(row) {
      return `¥${row.unit_price.toLocaleString()}`
    },
  },
  {
    title: '金额',
    key: 'amount',
    width: 100,
    render(row) {
      return `¥${row.amount.toLocaleString()}`
    },
  },
  {
    title: '供应商',
    key: 'supplier',
    width: 120,
    render(row) {
      return row.supplier?.name || '-'
    },
  },
  { title: '备注', key: 'remark', width: 150 },
]

const paymentColumns: DataTableColumns<Payment> = [
  {
    title: '金额',
    key: 'amount',
    width: 120,
    render(row) {
      return `¥${row.amount.toLocaleString()}`
    },
  },
  {
    title: '支付方式',
    key: 'method',
    width: 120,
    render(row) {
      const methodMap: Record<string, string> = {
        cash: '现金',
        bank_transfer: '银行卡',
        wechat: '微信',
        alipay: '支付宝',
        other: '其他',
      }
      return methodMap[row.method] || row.method
    },
  },
  {
    title: '支付时间',
    key: 'paid_at',
    width: 180,
    render(row) {
      if ((row as any).paid_at) {
        return new Date((row as any).paid_at).toLocaleString('zh-CN')
      }
      return new Date(row.created_at).toLocaleString('zh-CN')
    },
  },
  { title: '备注', key: 'remark' },
  {
    title: '记录时间',
    key: 'created_at',
    width: 180,
    render(row) {
      return new Date(row.created_at).toLocaleString('zh-CN')
    },
  },
]

async function fetchOrder() {
  loading.value = true
  try {
    order.value = await getOrder(orderId)
  } catch (err: any) {
    message.error(err.message || '获取订单详情失败')
  } finally {
    loading.value = false
  }
}

async function handleStatusUpdate(status: string) {
  try {
    await updateOrderStatus(orderId, status)
    message.success('状态更新成功')
    await fetchOrder()
  } catch (err: any) {
    message.error(err.message || '状态更新失败')
  }
}

function openPaymentModal() {
  paymentForm.value = {
    amount: null,
    method: null,
    paid_at: null,
    remark: '',
  }
  paymentModalVisible.value = true
}

async function handleAddPayment() {
  if (!paymentForm.value.amount || !paymentForm.value.method) {
    message.warning('请填写金额和支付方式')
    return
  }
  submitting.value = true
  try {
    const data: any = {
      amount: paymentForm.value.amount,
      method: paymentForm.value.method,
      remark: paymentForm.value.remark || undefined,
    }
    if (paymentForm.value.paid_at) {
      data.paid_at = new Date(paymentForm.value.paid_at).toISOString()
    }
    await addPayment(orderId, data)
    message.success('收款登记成功')
    paymentModalVisible.value = false
    await fetchOrder()
  } catch (err: any) {
    message.error(err.message || '收款登记失败')
  } finally {
    submitting.value = false
  }
}

function openCancelModal() {
  cancelReason.value = ''
  cancelModalVisible.value = true
}

async function handleCancel() {
  if (!cancelReason.value.trim()) {
    message.warning('请填写取消原因')
    return
  }
  submitting.value = true
  try {
    await createApproval({
      type: 'cancel',
      order_id: orderId,
      reason: cancelReason.value,
    })
    message.success('已提交取消审批申请')
    cancelModalVisible.value = false
  } catch (err: any) {
    message.error(err.message || '提交取消申请失败')
  } finally {
    submitting.value = false
  }
}

async function handleUploadContract({ file }: { file: UploadFileInfo }) {
  if (!file.file) return
  try {
    await uploadContract(orderId, file.file)
    message.success('合同上传成功')
    await fetchOrder()
  } catch (err: any) {
    message.error(err.message || '合同上传失败')
  }
}

async function handleDownloadQuote() {
  try {
    const blob = await getQuotePdf(orderId)
    const url = window.URL.createObjectURL(blob as unknown as Blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `报价单_${order.value?.order_no || orderId}.pdf`
    link.click()
    window.URL.revokeObjectURL(url)
  } catch (err: any) {
    message.error(err.message || '下载报价单失败')
  }
}

function handleBack() {
  router.push('/orders')
}

onMounted(() => {
  fetchOrder()
})
</script>

<template>
  <div>
    <NPageHeader
      :title="order ? `订单 ${order.order_no}` : '订单详情'"
      :subtitle="order ? getStatusTag(order.status).label : ''"
      @back="handleBack"
    >
      <template #back>返回</template>
      <template v-if="order" #extra>
        <NSpace>
          <NButton v-if="canSign" type="success" @click="handleStatusUpdate('signed')">
            签约
          </NButton>
          <NButton v-if="canExecute" type="warning" @click="handleStatusUpdate('executing')">
            开始执行
          </NButton>
          <NButton v-if="canComplete" @click="handleStatusUpdate('completed')">
            完成
          </NButton>
          <NPopconfirm v-if="canCancel" @positive-click="openCancelModal">
            <template #trigger>
              <NButton type="error">取消</NButton>
            </template>
            确认要取消此订单吗？取消需要审批。
          </NPopconfirm>
        </NSpace>
      </template>
    </NPageHeader>

    <NSpin :show="loading">
      <template v-if="order">
        <NCard style="margin-top: 16px" title="基本信息">
          <NDescriptions bordered :column="3" label-placement="left">
            <NDescriptionsItem label="订单号">{{ order.order_no }}</NDescriptionsItem>
            <NDescriptionsItem label="客户">
              {{ order.customer?.name || '-' }}
              <span v-if="order.customer?.phone" style="color: #999; margin-left: 8px">
                {{ order.customer.phone }}
              </span>
            </NDescriptionsItem>
            <NDescriptionsItem label="状态">
              <NTag :type="getStatusTag(order.status).type" size="small">
                {{ getStatusTag(order.status).label }}
              </NTag>
            </NDescriptionsItem>
            <NDescriptionsItem label="销售">
              {{ (order as any).sale?.name || '-' }}
            </NDescriptionsItem>
            <NDescriptionsItem label="策划">
              {{ (order as any).planner?.name || '-' }}
            </NDescriptionsItem>
            <NDescriptionsItem label="折扣">
              {{ order.discount ?? 1.0 }}
            </NDescriptionsItem>
            <NDescriptionsItem label="总金额">
              <span style="font-weight: 600">¥{{ order.total_amount.toLocaleString() }}</span>
            </NDescriptionsItem>
            <NDescriptionsItem label="已收金额">
              <span :style="{ color: order.paid_amount >= order.total_amount ? '#18a058' : '#f0a020' }">
                ¥{{ order.paid_amount.toLocaleString() }}
              </span>
            </NDescriptionsItem>
            <NDescriptionsItem label="创建时间">
              {{ new Date(order.created_at).toLocaleString('zh-CN') }}
            </NDescriptionsItem>
            <NDescriptionsItem v-if="order.remark" label="备注" :span="3">
              {{ order.remark }}
            </NDescriptionsItem>
          </NDescriptions>
        </NCard>

        <NCard style="margin-top: 16px" title="订单项目">
          <NDataTable
            :columns="itemColumns"
            :data="order.items || []"
            :row-key="(row: OrderItem) => row.id || row.name"
            :pagination="false"
            size="small"
          />
        </NCard>

        <NCard style="margin-top: 16px" title="收款记录">
          <template #header-extra>
            <NButton type="primary" size="small" @click="openPaymentModal">
              登记收款
            </NButton>
          </template>
          <NDataTable
            :columns="paymentColumns"
            :data="order.payments || []"
            :row-key="(row: Payment) => row.id"
            :pagination="false"
            size="small"
          />
          <div v-if="!order.payments?.length" style="text-align: center; color: #999; padding: 20px">
            暂无收款记录
          </div>
        </NCard>

        <NCard style="margin-top: 16px" title="合同">
          <template #header-extra>
            <NUpload
              :max="1"
              :show-file-list="false"
              :custom-request="({ file }) => handleUploadContract({ file })"
            >
              <NButton size="small">上传合同</NButton>
            </NUpload>
          </template>
          <div v-if="order.contract_url">
            <NSpace align="center">
              <span>合同文件：{{ order.contract_name || '已上传' }}</span>
              <NButton text type="primary" tag="a" :href="order.contract_url" target="_blank">
                查看/下载
              </NButton>
            </NSpace>
          </div>
          <div v-else style="color: #999">暂未上传合同</div>
        </NCard>

        <NSpace style="margin-top: 16px">
          <NButton @click="handleDownloadQuote">下载报价单 (PDF)</NButton>
        </NSpace>
      </template>
    </NSpin>

    <!-- 登记收款弹窗 -->
    <NModal
      v-model:show="paymentModalVisible"
      preset="dialog"
      title="登记收款"
      positive-text="确认"
      negative-text="取消"
      :loading="submitting"
      @positive-click="handleAddPayment"
    >
      <NForm label-placement="left" label-width="80">
        <NFormItem label="金额" required>
          <NInputNumber
            v-model:value="paymentForm.amount"
            :min="0.01"
            :precision="2"
            placeholder="收款金额"
            style="width: 100%"
          />
        </NFormItem>
        <NFormItem label="支付方式" required>
          <NSelect
            v-model:value="paymentForm.method"
            :options="methodOptions"
            placeholder="选择支付方式"
          />
        </NFormItem>
        <NFormItem label="支付时间">
          <NDatePicker
            v-model:value="paymentForm.paid_at"
            type="datetime"
            placeholder="选择支付时间"
            style="width: 100%"
          />
        </NFormItem>
        <NFormItem label="备注">
          <NInput
            v-model:value="paymentForm.remark"
            type="textarea"
            placeholder="备注信息"
            :rows="2"
          />
        </NFormItem>
      </NForm>
    </NModal>

    <!-- 取消订单弹窗 -->
    <NModal
      v-model:show="cancelModalVisible"
      preset="dialog"
      title="取消订单"
      positive-text="提交审批"
      negative-text="返回"
      :loading="submitting"
      @positive-click="handleCancel"
    >
      <NForm label-placement="left" label-width="80">
        <NFormItem label="取消原因" required>
          <NInput
            v-model:value="cancelReason"
            type="textarea"
            placeholder="请填写取消原因"
            :rows="3"
          />
        </NFormItem>
      </NForm>
    </NModal>
  </div>
</template>
