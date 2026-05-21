<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import {
  NModal,
  NCard,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NDatePicker,
  NButton,
  NSpace,
  useMessage,
  type FormRules,
  type FormInst,
} from 'naive-ui'
import {
  createCustomer,
  updateCustomer,
  getCustomer,
} from '@/api/customers'
import type { Customer } from '@/api/customers'

const props = defineProps<{
  visible: boolean
  customerId: number | null
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'success'): void
}>()

const message = useMessage()
const formRef = ref<FormInst | null>(null)
const loading = ref(false)

const genderOptions = [
  { label: '男', value: 'male' },
  { label: '女', value: 'female' },
  { label: '未知', value: 'unknown' },
]

const sourceOptions = [
  { label: '线上咨询', value: 'online' },
  { label: '电话咨询', value: 'phone' },
  { label: '到店咨询', value: 'visit' },
  { label: '朋友推荐', value: 'referral' },
  { label: '婚礼展会', value: 'exhibition' },
  { label: '其他', value: 'other' },
]

const statusOptions = [
  { label: '潜在客户', value: 'potential' },
  { label: '跟进中', value: 'following' },
  { label: '有意向', value: 'intention' },
  { label: '已签约', value: 'signed' },
  { label: '已流失', value: 'lost' },
]

const formData = reactive({
  name: '',
  phone: '',
  gender: null as string | null,
  source: null as string | null,
  status: 'potential' as string,
  budget: null as number | null,
  wedding_date: null as number | null,
  note: '',
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入客户姓名', trigger: 'blur' },
  ],
  phone: [
    { required: true, message: '请输入手机号码', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的11位手机号码', trigger: 'blur' },
  ],
}

const title = computed(() => (props.customerId ? '编辑客户' : '新增客户'))

const showModal = computed({
  get: () => props.visible,
  set: (val: boolean) => emit('update:visible', val),
})

watch(() => props.visible, async (val) => {
  if (val) {
    resetForm()
    if (props.customerId) {
      await fetchCustomerDetail()
    }
  }
})

async function fetchCustomerDetail() {
  if (!props.customerId) return
  try {
    loading.value = true
    const customer = await getCustomer(props.customerId)
    formData.name = customer.name || ''
    formData.phone = customer.phone || ''
    formData.gender = customer.gender || null
    formData.source = customer.source || null
    formData.status = customer.status || 'potential'
    formData.budget = customer.budget || null
    formData.wedding_date = customer.wedding_date
      ? new Date(customer.wedding_date).getTime()
      : null
    formData.note = ''
  } catch (err: any) {
    message.error(err.message || '获取客户信息失败')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  formData.name = ''
  formData.phone = ''
  formData.gender = null
  formData.source = null
  formData.status = 'potential'
  formData.budget = null
  formData.wedding_date = null
  formData.note = ''
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  loading.value = true
  try {
    const payload: Partial<Customer> = {
      name: formData.name,
      phone: formData.phone,
      gender: formData.gender || undefined,
      source: formData.source || undefined,
      status: formData.status,
      budget: formData.budget || undefined,
      wedding_date: formData.wedding_date
        ? new Date(formData.wedding_date).toISOString().split('T')[0]
        : undefined,
    }
    ;(payload as any).note = formData.note || undefined

    if (props.customerId) {
      await updateCustomer(props.customerId, payload)
      message.success('客户信息已更新')
    } else {
      await createCustomer(payload)
      message.success('客户创建成功')
    }

    showModal.value = false
    emit('success')
  } catch (err: any) {
    message.error(err.message || '操作失败')
  } finally {
    loading.value = false
  }
}

function handleCancel() {
  showModal.value = false
}
</script>

<template>
  <NModal
    v-model:show="showModal"
    :mask-closable="false"
    preset="card"
    :title="title"
    style="width: 600px"
  >
    <NForm
      ref="formRef"
      :model="formData"
      :rules="rules"
      label-placement="left"
      label-width="80"
    >
      <NFormItem label="姓名" path="name">
        <NInput v-model:value="formData.name" placeholder="请输入客户姓名" />
      </NFormItem>
      <NFormItem label="手机" path="phone">
        <NInput v-model:value="formData.phone" placeholder="请输入11位手机号码" maxlength="11" />
      </NFormItem>
      <NFormItem label="性别" path="gender">
        <NSelect
          v-model:value="formData.gender"
          :options="genderOptions"
          placeholder="请选择性别"
          clearable
        />
      </NFormItem>
      <NFormItem label="来源" path="source">
        <NSelect
          v-model:value="formData.source"
          :options="sourceOptions"
          placeholder="请选择客户来源"
          clearable
        />
      </NFormItem>
      <NFormItem label="状态" path="status">
        <NSelect
          v-model:value="formData.status"
          :options="statusOptions"
          placeholder="请选择客户状态"
        />
      </NFormItem>
      <NFormItem label="预算" path="budget">
        <NInput
          v-model:value="(formData.budget as any)"
          placeholder="请输入预算金额"
          type="number"
          clearable
          @update:value="(val: string) => formData.budget = val ? Number(val) : null"
        />
      </NFormItem>
      <NFormItem label="婚期" path="wedding_date">
        <NDatePicker
          v-model:value="formData.wedding_date"
          type="date"
          placeholder="请选择婚期"
          clearable
          style="width: 100%"
        />
      </NFormItem>
      <NFormItem label="备注" path="note">
        <NInput
          v-model:value="formData.note"
          type="textarea"
          placeholder="请输入备注信息"
          :rows="3"
        />
      </NFormItem>
    </NForm>
    <template #footer>
      <NSpace justify="end">
        <NButton @click="handleCancel">取消</NButton>
        <NButton type="primary" :loading="loading" @click="handleSubmit">
          {{ customerId ? '保存' : '创建' }}
        </NButton>
      </NSpace>
    </template>
  </NModal>
</template>
