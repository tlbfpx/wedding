<script setup lang="ts">
import { ref, reactive, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard,
  NPageHeader,
  NButton,
  NSpace,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NSelect,
  NDataTable,
  NDivider,
  NSpin,
  NAlert,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns, FormInst, FormRules } from 'naive-ui'
import { createOrder } from '@/api/orders'
import type { OrderItem } from '@/api/orders'
import { getCustomers } from '@/api/customers'
import type { Customer } from '@/api/customers'
import { getUsers } from '@/api/users'
import type { User } from '@/api/users'
import { getSuppliers } from '@/api/suppliers'
import type { Supplier } from '@/api/suppliers'

const router = useRouter()
const message = useMessage()

const formRef = ref<FormInst | null>(null)
const submitting = ref(false)
const loadingOptions = ref(false)

const customerOptions = ref<{ label: string; value: number }[]>([])
const plannerOptions = ref<{ label: string; value: number }[]>([])
const supplierOptions = ref<{ label: string; value: number }[]>([])

const itemTypeOptions = [
  { label: '场地', value: 'venue' },
  { label: '主持', value: 'host' },
  { label: '摄影', value: 'photography' },
  { label: '摄像', value: 'videography' },
  { label: '化妆', value: 'makeup' },
  { label: '花艺', value: 'floral' },
  { label: '灯光音响', value: 'av' },
  { label: '甜品', value: 'dessert' },
  { label: '婚纱', value: 'dress' },
  { label: '其他', value: 'other' },
]

const formData = reactive({
  customer_id: null as number | null,
  planner_id: null as number | null,
  discount: 1.0,
  remark: '',
})

const orderItems = ref<OrderItem[]>([])

const rules: FormRules = {
  customer_id: {
    required: true,
    type: 'number',
    message: '请选择客户',
    trigger: 'change',
  },
}

const showDiscountWarning = computed(() => {
  return formData.discount < 0.9
})

const totalAmount = computed(() => {
  return orderItems.value.reduce((sum, item) => {
    return sum + item.quantity * item.unit_price
  }, 0)
})

const discountedTotal = computed(() => {
  return totalAmount.value * formData.discount
})

const itemColumns: DataTableColumns<OrderItem> = [
  {
    title: '类型',
    key: 'type',
    width: 130,
    render(row, index) {
      return h(NSelect, {
        value: row.type,
        options: itemTypeOptions,
        placeholder: '选择类型',
        size: 'small',
        style: 'width: 120px',
        'onUpdate:value': (val: string) => {
          orderItems.value[index].type = val
        },
      })
    },
  },
  {
    title: '名称',
    key: 'name',
    width: 150,
    render(row, index) {
      return h(NInput, {
        value: row.name,
        placeholder: '项目名称',
        size: 'small',
        'onUpdate:value': (val: string) => {
          orderItems.value[index].name = val
        },
      })
    },
  },
  {
    title: '数量',
    key: 'quantity',
    width: 100,
    render(row, index) {
      return h(NInputNumber, {
        value: row.quantity,
        min: 1,
        size: 'small',
        style: 'width: 80px',
        'onUpdate:value': (val: number | null) => {
          orderItems.value[index].quantity = val || 1
          orderItems.value[index].amount =
            orderItems.value[index].quantity * orderItems.value[index].unit_price
        },
      })
    },
  },
  {
    title: '单价',
    key: 'unit_price',
    width: 120,
    render(row, index) {
      return h(NInputNumber, {
        value: row.unit_price,
        min: 0,
        precision: 2,
        size: 'small',
        style: 'width: 100px',
        'onUpdate:value': (val: number | null) => {
          orderItems.value[index].unit_price = val || 0
          orderItems.value[index].amount =
            orderItems.value[index].quantity * orderItems.value[index].unit_price
        },
      })
    },
  },
  {
    title: '金额',
    key: 'amount',
    width: 120,
    render(row) {
      return `¥${row.amount.toLocaleString()}`
    },
  },
  {
    title: '供应商',
    key: 'supplier_id',
    width: 150,
    render(row, index) {
      return h(NSelect, {
        value: row.supplier_id || null,
        options: supplierOptions.value,
        placeholder: '选择供应商',
        size: 'small',
        clearable: true,
        style: 'width: 140px',
        'onUpdate:value': (val: number | null) => {
          orderItems.value[index].supplier_id = val || undefined
        },
      })
    },
  },
  {
    title: '备注',
    key: 'remark',
    width: 150,
    render(row, index) {
      return h(NInput, {
        value: row.remark || '',
        placeholder: '备注',
        size: 'small',
        'onUpdate:value': (val: string) => {
          orderItems.value[index].remark = val
        },
      })
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    fixed: 'right',
    render(_, index) {
      return h(
        NButton,
        {
          size: 'small',
          type: 'error',
          text: true,
          onClick: () => {
            orderItems.value.splice(index, 1)
          },
        },
        { default: () => '删除' },
      )
    },
  },
]

function addItem() {
  orderItems.value.push({
    type: '',
    name: '',
    quantity: 1,
    unit_price: 0,
    amount: 0,
    supplier_id: undefined,
    remark: '',
  })
}

async function handleSearchCustomer(keyword: string) {
  if (!keyword) return
  try {
    const res = await getCustomers({ keyword, page_size: 20 })
    customerOptions.value = res.items.map((c: Customer) => ({
      label: `${c.name} (${c.phone})`,
      value: c.id,
    }))
  } catch {
    // silently ignore
  }
}

async function loadOptions() {
  loadingOptions.value = true
  try {
    const [usersRes, suppliersRes] = await Promise.allSettled([
      getUsers({ page_size: 100 }),
      getSuppliers({ page_size: 100 }),
    ])
    if (usersRes.status === 'fulfilled') {
      plannerOptions.value = usersRes.value.items.map((u: User) => ({
        label: u.name,
        value: u.id,
      }))
    }
    if (suppliersRes.status === 'fulfilled') {
      supplierOptions.value = suppliersRes.value.items.map((s: Supplier) => ({
        label: s.name,
        value: s.id,
      }))
    }
  } finally {
    loadingOptions.value = false
  }
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  if (orderItems.value.length === 0) {
    message.warning('请至少添加一个订单项目')
    return
  }

  const hasInvalid = orderItems.value.some((item) => !item.type || !item.name || item.unit_price <= 0)
  if (hasInvalid) {
    message.warning('请完善订单项目信息（类型、名称、单价不能为空）')
    return
  }

  submitting.value = true
  try {
    await createOrder({
      customer_id: formData.customer_id!,
      planner_id: formData.planner_id || undefined,
      discount: formData.discount,
      remark: formData.remark || undefined,
      items: orderItems.value.map((item) => ({
        type: item.type,
        name: item.name,
        quantity: item.quantity,
        unit_price: item.unit_price,
        amount: item.amount,
        supplier_id: item.supplier_id,
        remark: item.remark,
      })),
    })
    message.success('订单创建成功')
    router.push('/orders')
  } catch (err: any) {
    message.error(err.message || '创建订单失败')
  } finally {
    submitting.value = false
  }
}

function handleBack() {
  router.push('/orders')
}

onMounted(() => {
  loadOptions()
  addItem()
})
</script>

<template>
  <div>
    <NPageHeader title="新建订单" subtitle="创建新的订单" @back="handleBack">
      <template #back>返回</template>
    </NPageHeader>

    <NSpin :show="loadingOptions">
      <NCard style="margin-top: 16px">
        <NForm
          ref="formRef"
          :model="formData"
          :rules="rules"
          label-placement="left"
          label-width="100"
        >
          <NFormItem label="客户" path="customer_id">
            <NSelect
              v-model:value="formData.customer_id"
              :options="customerOptions"
              placeholder="搜索客户姓名/电话"
              filterable
              remote
              style="width: 300px"
              @search="handleSearchCustomer"
            />
          </NFormItem>

          <NFormItem label="策划师" path="planner_id">
            <NSelect
              v-model:value="formData.planner_id"
              :options="plannerOptions"
              placeholder="选择策划师"
              filterable
              clearable
              style="width: 300px"
            />
          </NFormItem>

          <NFormItem label="折扣" path="discount">
            <NInputNumber
              v-model:value="formData.discount"
              :min="0.01"
              :max="1.0"
              :step="0.05"
              :precision="2"
              style="width: 200px"
            />
          </NFormItem>

          <NAlert v-if="showDiscountWarning" type="warning" style="margin-bottom: 16px">
            当前折扣低于 9 折，提交后将需要上级审批
          </NAlert>

          <NFormItem label="备注" path="remark">
            <NInput
              v-model:value="formData.remark"
              type="textarea"
              placeholder="订单备注"
              :rows="3"
              style="width: 500px"
            />
          </NFormItem>
        </NForm>
      </NCard>

      <NCard title="订单项目" style="margin-top: 16px">
        <template #header-extra>
          <NButton type="primary" size="small" @click="addItem">添加项目</NButton>
        </template>

        <NDataTable
          :columns="itemColumns"
          :data="orderItems"
          :row-key="(_: OrderItem, index: number) => index"
          :pagination="false"
          :scroll-x="1050"
          size="small"
        />

        <NDivider />

        <NSpace justify="end" align="center" :size="24">
          <span>
            原价合计：<strong>¥{{ totalAmount.toLocaleString() }}</strong>
          </span>
          <span>
            折后合计：<strong style="font-size: 18px; color: #18a058">
              ¥{{ discountedTotal.toLocaleString() }}
            </strong>
          </span>
        </NSpace>
      </NCard>

      <NSpace justify="end" style="margin-top: 16px">
        <NButton @click="handleBack">取消</NButton>
        <NButton type="primary" :loading="submitting" @click="handleSubmit">
          提交订单
        </NButton>
      </NSpace>
    </NSpin>
  </div>
</template>
