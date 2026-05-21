<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import {
  NPageHeader,
  NButton,
  NCard,
  NSpace,
  NDataTable,
  NModal,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NRate,
  NTag,
  useMessage,
  type DataTableColumns,
  type FormInst,
  type FormRules,
  type SelectOption,
} from 'naive-ui'
import {
  getSuppliers,
  createSupplier,
  updateSupplier,
} from '@/api/suppliers'
import type { Supplier } from '@/api/suppliers'

const router = useRouter()
const message = useMessage()

const loading = ref(false)
const suppliers = ref<Supplier[]>([])
const total = ref(0)
const pagination = reactive({
  page: 1,
  pageSize: 20,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
})

// Filters
const filters = reactive({
  type: null as string | null,
  status: null as string | null,
  keyword: '',
  rating_min: null as number | null,
})

const typeOptions: SelectOption[] = [
  { label: '四大金刚', value: 'four_gems' },
  { label: '婚车', value: 'wedding_car' },
  { label: '场地', value: 'venue' },
  { label: '花艺', value: 'floral' },
  { label: '摄影摄像', value: 'photo_video' },
  { label: '主持', value: 'host' },
  { label: '其他', value: 'other' },
]

const typeLabelMap: Record<string, string> = {
  four_gems: '四大金刚',
  wedding_car: '婚车',
  venue: '场地',
  floral: '花艺',
  photo_video: '摄影摄像',
  host: '主持',
  other: '其他',
}

const typeColorMap: Record<string, string> = {
  four_gems: 'error',
  wedding_car: 'info',
  venue: 'success',
  floral: 'warning',
  photo_video: 'default',
  host: 'info',
  other: 'default',
}

const statusOptions: SelectOption[] = [
  { label: '合作中', value: 'active' },
  { label: '已停用', value: 'inactive' },
  { label: '待审核', value: 'pending' },
]

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

// Modal
const showModal = ref(false)
const modalLoading = ref(false)
const editingSupplier = ref<Supplier | null>(null)
const formRef = ref<FormInst | null>(null)
const formValue = ref({
  name: '',
  type: null as string | null,
  contact_name: '',
  contact_phone: '',
  address: '',
  status: 'active' as string,
  remark: '',
})

const formRules: FormRules = {
  name: { required: true, message: '请输入供应商名称', trigger: 'blur' },
  type: { required: true, message: '请选择类型', trigger: 'change' },
  contact_name: { required: true, message: '请输入联系人', trigger: 'blur' },
  contact_phone: { required: true, message: '请输入联系电话', trigger: 'blur' },
}

const columns: DataTableColumns<Supplier> = [
  { title: '名称', key: 'name', width: 160 },
  {
    title: '类型',
    key: 'type',
    width: 110,
    render(row) {
      return h(NTag, { type: typeColorMap[row.type] as any, size: 'small' }, {
        default: () => typeLabelMap[row.type] || row.type,
      })
    },
  },
  { title: '联系人', key: 'contact_name', width: 100 },
  { title: '电话', key: 'contact_phone', width: 130 },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render(row) {
      return h(NTag, { type: statusColorMap[row.status] as any, size: 'small' }, {
        default: () => statusLabelMap[row.status] || row.status,
      })
    },
  },
  {
    title: '评分',
    key: 'rating',
    width: 120,
    render() {
      // Rating will be displayed when API returns it
      return h(NRate, { size: 'small', allowHalf: true, value: 0, readonly: true })
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    render(row) {
      return h(NButton, {
        size: 'small',
        quaternary: true,
        onClick: () => router.push(`/suppliers/${row.id}`),
      }, { default: () => '查看' })
    },
  },
]

async function fetchSuppliers() {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (filters.type) params.type = filters.type
    if (filters.status) params.status = filters.status
    if (filters.keyword) params.keyword = filters.keyword
    const res = await getSuppliers(params)
    suppliers.value = res.items
    total.value = res.total
  } catch (err: any) {
    message.error(err.message || '获取供应商列表失败')
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  pagination.page = page
  fetchSuppliers()
}

function handlePageSizeChange(pageSize: number) {
  pagination.pageSize = pageSize
  pagination.page = 1
  fetchSuppliers()
}

function handleSearch() {
  pagination.page = 1
  fetchSuppliers()
}

function openCreateModal() {
  editingSupplier.value = null
  formValue.value = {
    name: '',
    type: null,
    contact_name: '',
    contact_phone: '',
    address: '',
    status: 'active',
    remark: '',
  }
  showModal.value = true
}

function openEditModal(supplier: Supplier) {
  editingSupplier.value = supplier
  formValue.value = {
    name: supplier.name,
    type: supplier.type,
    contact_name: supplier.contact_name,
    contact_phone: supplier.contact_phone,
    address: supplier.address || '',
    status: supplier.status,
    remark: supplier.remark || '',
  }
  showModal.value = true
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  modalLoading.value = true
  try {
    const data = {
      name: formValue.value.name,
      type: formValue.value.type!,
      contact_name: formValue.value.contact_name,
      contact_phone: formValue.value.contact_phone,
      address: formValue.value.address || undefined,
      status: formValue.value.status,
      remark: formValue.value.remark || undefined,
    }
    if (editingSupplier.value) {
      await updateSupplier(editingSupplier.value.id, data)
      message.success('供应商更新成功')
    } else {
      await createSupplier(data)
      message.success('供应商创建成功')
    }
    showModal.value = false
    fetchSuppliers()
  } catch (err: any) {
    message.error(err.message || '操作失败')
  } finally {
    modalLoading.value = false
  }
}

onMounted(() => {
  fetchSuppliers()
})
</script>

<template>
  <div>
    <NPageHeader title="供应商管理">
      <template #extra>
        <NButton type="primary" @click="openCreateModal">新增供应商</NButton>
      </template>
    </NPageHeader>

    <NCard style="margin-top: 16px;">
      <NSpace align="center" style="margin-bottom: 16px;" :wrap="true">
        <NSelect
          v-model:value="filters.type"
          :options="typeOptions"
          placeholder="供应商类型"
          clearable
          style="width: 140px;"
        />
        <NSelect
          v-model:value="filters.status"
          :options="statusOptions"
          placeholder="状态"
          clearable
          style="width: 120px;"
        />
        <NInput
          v-model:value="filters.keyword"
          placeholder="搜索名称/联系人"
          clearable
          style="width: 200px;"
          @keyup.enter="handleSearch"
        />
        <NButton type="primary" @click="handleSearch">查询</NButton>
      </NSpace>

      <NDataTable
        :columns="columns"
        :data="suppliers"
        :loading="loading"
        :bordered="false"
        :pagination="{
          page: pagination.page,
          pageSize: pagination.pageSize,
          itemCount: total,
          showSizePicker: pagination.showSizePicker,
          pageSizes: pagination.pageSizes,
          onPageChange: handlePageChange,
          onPageSizeChange: handlePageSizeChange,
        }"
        :row-key="(row: Supplier) => row.id"
      />
    </NCard>

    <!-- Create/Edit Supplier Modal -->
    <NModal
      v-model:show="showModal"
      preset="card"
      :title="editingSupplier ? '编辑供应商' : '新增供应商'"
      style="width: 560px;"
      :mask-closable="false"
    >
      <NForm
        ref="formRef"
        :model="formValue"
        :rules="formRules"
        label-placement="left"
        label-width="80"
      >
        <NFormItem path="name" label="名称">
          <NInput v-model:value="formValue.name" placeholder="请输入供应商名称" />
        </NFormItem>
        <NFormItem path="type" label="类型">
          <NSelect
            v-model:value="formValue.type"
            :options="typeOptions"
            placeholder="请选择类型"
          />
        </NFormItem>
        <NFormItem path="contact_name" label="联系人">
          <NInput v-model:value="formValue.contact_name" placeholder="请输入联系人" />
        </NFormItem>
        <NFormItem path="contact_phone" label="电话">
          <NInput v-model:value="formValue.contact_phone" placeholder="请输入联系电话" />
        </NFormItem>
        <NFormItem path="address" label="地址">
          <NInput v-model:value="formValue.address" placeholder="请输入地址" />
        </NFormItem>
        <NFormItem path="status" label="状态">
          <NSelect
            v-model:value="formValue.status"
            :options="statusOptions"
            placeholder="请选择状态"
          />
        </NFormItem>
        <NFormItem path="remark" label="备注">
          <NInput v-model:value="formValue.remark" type="textarea" placeholder="请输入备注" :rows="3" />
        </NFormItem>
      </NForm>
      <template #action>
        <NSpace justify="end">
          <NButton @click="showModal = false">取消</NButton>
          <NButton type="primary" :loading="modalLoading" @click="handleSubmit">确定</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>
