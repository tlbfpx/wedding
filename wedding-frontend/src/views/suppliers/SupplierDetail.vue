<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  NPageHeader,
  NButton,
  NCard,
  NSpace,
  NDescriptions,
  NDescriptionsItem,
  NDataTable,
  NTag,
  NRate,
  NModal,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NEmpty,
  useMessage,
  type DataTableColumns,
  type FormInst,
  type FormRules,
} from 'naive-ui'
import {
  getSupplier,
  updateSupplier,
  getSupplierServices,
  addSupplierService,
  updateSupplierService,
  getSupplierEvaluations,
  addSupplierEvaluation,
} from '@/api/suppliers'
import type { Supplier, SupplierService, SupplierEvaluation } from '@/api/suppliers'

const router = useRouter()
const route = useRoute()
const message = useMessage()

const supplierId = computed(() => Number(route.params.id))
const loading = ref(false)
const supplier = ref<Supplier | null>(null)

const typeLabelMap: Record<string, string> = {
  four_gems: '四大金刚',
  wedding_car: '婚车',
  venue: '场地',
  floral: '花艺',
  photo_video: '摄影摄像',
  host: '主持',
  other: '其他',
}

const statusLabelMap: Record<string, string> = {
  active: '合作中',
  inactive: '已停用',
  pending: '待审核',
}

const statusColorMap: Record<string, string> = {
  active: 'success',
  inactive: 'default',
  pending: 'warning',
}

// Services
const services = ref<SupplierService[]>([])
const serviceLoading = ref(false)
const showServiceModal = ref(false)
const editingService = ref<SupplierService | null>(null)
const serviceFormRef = ref<FormInst | null>(null)
const serviceForm = ref({
  name: '',
  description: '',
  unit_price: null as number | null,
  unit: '',
  note: '',
})
const serviceRules: FormRules = {
  name: { required: true, message: '请输入服务名称', trigger: 'blur' },
}

const serviceColumns: DataTableColumns<SupplierService> = [
  { title: '服务名称', key: 'name', width: 140 },
  { title: '描述', key: 'description', width: 200, ellipsis: { tooltip: true } },
  {
    title: '单价',
    key: 'unit_price',
    width: 100,
    render(row) {
      return row.unit_price != null ? `¥${row.unit_price.toLocaleString()}` : '-'
    },
  },
  { title: '单位', key: 'unit', width: 80 },
  { title: '备注', key: 'note', width: 150, ellipsis: { tooltip: true } },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    render(row) {
      return h(NButton, {
        size: 'small',
        quaternary: true,
        onClick: () => openEditServiceModal(row),
      }, { default: () => '编辑' })
    },
  },
]

// Evaluations
const evaluations = ref<SupplierEvaluation[]>([])
const evaluationLoading = ref(false)
const showEvalModal = ref(false)
const evalFormRef = ref<FormInst | null>(null)
const evalForm = ref({
  rating: 5,
  comment: '',
})
const evalRules: FormRules = {
  rating: { required: true, type: 'number', message: '请选择评分', trigger: 'change' },
}

async function fetchSupplier() {
  loading.value = true
  try {
    supplier.value = await getSupplier(supplierId.value)
  } catch (err: any) {
    message.error(err.message || '获取供应商详情失败')
  } finally {
    loading.value = false
  }
}

async function fetchServices() {
  serviceLoading.value = true
  try {
    services.value = await getSupplierServices(supplierId.value)
  } catch {
    // Silently handle
  } finally {
    serviceLoading.value = false
  }
}

async function fetchEvaluations() {
  evaluationLoading.value = true
  try {
    evaluations.value = await getSupplierEvaluations(supplierId.value)
  } catch {
    // Silently handle
  } finally {
    evaluationLoading.value = false
  }
}

// Service modal
function openAddServiceModal() {
  editingService.value = null
  serviceForm.value = {
    name: '',
    description: '',
    unit_price: null,
    unit: '',
    note: '',
  }
  showServiceModal.value = true
}

function openEditServiceModal(service: SupplierService) {
  editingService.value = service
  serviceForm.value = {
    name: service.name,
    description: service.description || '',
    unit_price: service.unit_price ?? null,
    unit: '',
    note: '',
  }
  showServiceModal.value = true
}

async function handleServiceSubmit() {
  try {
    await serviceFormRef.value?.validate()
  } catch {
    return
  }
  try {
    const data = {
      name: serviceForm.value.name,
      description: serviceForm.value.description || undefined,
      unit_price: serviceForm.value.unit_price ?? undefined,
      category: 'general',
    }
    if (editingService.value) {
      await updateSupplierService(supplierId.value, editingService.value.id, data)
      message.success('服务更新成功')
    } else {
      await addSupplierService(supplierId.value, data)
      message.success('服务添加成功')
    }
    showServiceModal.value = false
    fetchServices()
  } catch (err: any) {
    message.error(err.message || '操作失败')
  }
}

// Evaluation modal
function openEvalModal() {
  evalForm.value = { rating: 5, comment: '' }
  showEvalModal.value = true
}

async function handleEvalSubmit() {
  try {
    await evalFormRef.value?.validate()
  } catch {
    return
  }
  try {
    await addSupplierEvaluation(supplierId.value, {
      rating: evalForm.value.rating,
      comment: evalForm.value.comment || undefined,
    })
    message.success('评价添加成功')
    showEvalModal.value = false
    fetchEvaluations()
  } catch (err: any) {
    message.error(err.message || '添加评价失败')
  }
}

onMounted(async () => {
  await fetchSupplier()
  fetchServices()
  fetchEvaluations()
})
</script>

<template>
  <div v-if="supplier">
    <NButton text style="margin-bottom: 16px;" @click="router.push('/suppliers')">
      &lt; 返回供应商列表
    </NButton>

    <NPageHeader :title="supplier.name">
      <template #extra>
        <NTag :type="statusColorMap[supplier.status] as any">
          {{ statusLabelMap[supplier.status] || supplier.status }}
        </NTag>
      </template>
    </NPageHeader>

    <NCard title="基本信息" style="margin-top: 16px;">
      <NDescriptions bordered :column="3">
        <NDescriptionsItem label="供应商名称">{{ supplier.name }}</NDescriptionsItem>
        <NDescriptionsItem label="类型">
          <NTag size="small">{{ typeLabelMap[supplier.type] || supplier.type }}</NTag>
        </NDescriptionsItem>
        <NDescriptionsItem label="联系人">{{ supplier.contact_name }}</NDescriptionsItem>
        <NDescriptionsItem label="电话">{{ supplier.contact_phone }}</NDescriptionsItem>
        <NDescriptionsItem label="地址">{{ supplier.address || '-' }}</NDescriptionsItem>
        <NDescriptionsItem label="状态">
          <NTag :type="statusColorMap[supplier.status] as any" size="small">
            {{ statusLabelMap[supplier.status] || supplier.status }}
          </NTag>
        </NDescriptionsItem>
        <NDescriptionsItem label="备注" :span="3">{{ supplier.remark || '-' }}</NDescriptionsItem>
      </NDescriptions>
    </NCard>

    <!-- Services Section -->
    <NCard title="服务项目" style="margin-top: 16px;">
      <template #header-extra>
        <NButton type="primary" size="small" @click="openAddServiceModal">添加服务</NButton>
      </template>
      <NDataTable
        :columns="serviceColumns"
        :data="services"
        :loading="serviceLoading"
        :bordered="false"
      />
    </NCard>

    <!-- Evaluations Section -->
    <NCard title="评价记录" style="margin-top: 16px;">
      <template #header-extra>
        <NButton type="primary" size="small" @click="openEvalModal">添加评价</NButton>
      </template>

      <NEmpty v-if="evaluations.length === 0 && !evaluationLoading" description="暂无评价" />

      <div v-else>
        <div
          v-for="evaluation in evaluations"
          :key="evaluation.id"
          style="padding: 12px 0; border-bottom: 1px solid #f0f0f0;"
        >
          <NSpace align="center" justify="space-between">
            <NSpace align="center">
              <NRate :value="evaluation.rating" readonly allow-half size="small" />
              <span style="color: #999; font-size: 13px;">
                {{ evaluation.evaluator?.name || '匿名' }}
              </span>
            </NSpace>
            <span style="color: #999; font-size: 12px;">{{ evaluation.created_at }}</span>
          </NSpace>
          <div v-if="evaluation.comment" style="margin-top: 8px; color: #333; font-size: 14px;">
            {{ evaluation.comment }}
          </div>
        </div>
      </div>
    </NCard>

    <!-- Service Modal -->
    <NModal
      v-model:show="showServiceModal"
      preset="card"
      :title="editingService ? '编辑服务' : '添加服务'"
      style="width: 480px;"
      :mask-closable="false"
    >
      <NForm
        ref="serviceFormRef"
        :model="serviceForm"
        :rules="serviceRules"
        label-placement="left"
        label-width="80"
      >
        <NFormItem path="name" label="服务名称">
          <NInput v-model:value="serviceForm.name" placeholder="请输入服务名称" />
        </NFormItem>
        <NFormItem path="description" label="描述">
          <NInput v-model:value="serviceForm.description" type="textarea" placeholder="请输入描述" :rows="2" />
        </NFormItem>
        <NFormItem path="unit_price" label="单价">
          <NInputNumber v-model:value="serviceForm.unit_price" :min="0" style="width: 100%;" placeholder="请输入单价">
            <template #prefix>¥</template>
          </NInputNumber>
        </NFormItem>
        <NFormItem path="unit" label="单位">
          <NInput v-model:value="serviceForm.unit" placeholder="如: 次/天/套" />
        </NFormItem>
        <NFormItem path="note" label="备注">
          <NInput v-model:value="serviceForm.note" type="textarea" placeholder="请输入备注" :rows="2" />
        </NFormItem>
      </NForm>
      <template #action>
        <NSpace justify="end">
          <NButton @click="showServiceModal = false">取消</NButton>
          <NButton type="primary" @click="handleServiceSubmit">确定</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Evaluation Modal -->
    <NModal
      v-model:show="showEvalModal"
      preset="card"
      title="添加评价"
      style="width: 440px;"
      :mask-closable="false"
    >
      <NForm
        ref="evalFormRef"
        :model="evalForm"
        :rules="evalRules"
        label-placement="left"
        label-width="60"
      >
        <NFormItem path="rating" label="评分">
          <NRate v-model:value="evalForm.rating" allow-half />
        </NFormItem>
        <NFormItem path="comment" label="内容">
          <NInput
            v-model:value="evalForm.comment"
            type="textarea"
            placeholder="请输入评价内容"
            :rows="4"
          />
        </NFormItem>
      </NForm>
      <template #action>
        <NSpace justify="end">
          <NButton @click="showEvalModal = false">取消</NButton>
          <NButton type="primary" @click="handleEvalSubmit">确定</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>
