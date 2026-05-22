<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NPageHeader,
  NButton,
  NSpace,
  NCard,
  NDescriptions,
  NDescriptionsItem,
  NTag,
  NTimeline,
  NTimelineItem,
  NModal,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NDatePicker,
  NEmpty,
  useMessage,
  type FormInst,
} from 'naive-ui'
import { getCustomer, addFollowUp } from '@/api/customers'
import type { Customer, FollowUp } from '@/api/customers'
import CustomerForm from './CustomerForm.vue'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const customerId = computed(() => Number(route.params.id))

// --- State ---
const loading = ref(false)
const customer = ref<Customer | null>(null)

// Edit modal
const editVisible = ref(false)

// Follow-up modal
const followUpVisible = ref(false)
const followUpLoading = ref(false)
const followUpFormRef = ref<FormInst | null>(null)
const followUpForm = ref({
  type: null as string | null,
  content: '',
  next_follow_up_at: null as number | null,
})

const followUpTypeOptions = [
  { label: '电话', value: 'phone' },
  { label: '微信', value: 'wechat' },
  { label: '面访', value: 'visit' },
  { label: '其他', value: 'other' },
]

// --- Helpers ---
const statusMap: Record<string, { label: string; type: 'default' | 'info' | 'warning' | 'success' | 'error' }> = {
  potential: { label: '潜在客户', type: 'default' },
  following: { label: '跟进中', type: 'info' },
  intention: { label: '有意向', type: 'warning' },
  signed: { label: '已签约', type: 'success' },
  lost: { label: '已流失', type: 'error' },
}

const genderMap: Record<string, string> = {
  male: '男',
  female: '女',
  unknown: '未知',
}

const sourceMap: Record<string, string> = {
  online: '线上咨询',
  phone: '电话咨询',
  visit: '到店咨询',
  referral: '朋友推荐',
  exhibition: '婚礼展会',
  other: '其他',
}

const followUpTypeLabel: Record<string, string> = {
  phone: '电话',
  wechat: '微信',
  visit: '面访',
  other: '其他',
}

function formatDate(dateStr?: string | null) {
  if (!dateStr) return '-'
  return dateStr.split('T')[0]
}

function formatDateTime(dateStr?: string | null) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function formatBudget(budget?: number | null) {
  if (!budget) return '-'
  return `¥${budget.toLocaleString()}`
}

// --- Data fetching ---
async function fetchCustomer() {
  loading.value = true
  try {
    customer.value = await getCustomer(customerId.value)
  } catch (err: any) {
    message.error(err.message || '获取客户详情失败')
  } finally {
    loading.value = false
  }
}

// --- Event handlers ---
function goBack() {
  router.push('/customers')
}

function handleEdit() {
  editVisible.value = true
}

function handleAddFollowUp() {
  followUpForm.value = {
    type: null,
    content: '',
    next_follow_up_at: null,
  }
  followUpVisible.value = true
}

async function submitFollowUp() {
  if (!followUpForm.value.type) {
    message.warning('请选择跟进方式')
    return
  }
  if (!followUpForm.value.content.trim()) {
    message.warning('请输入跟进内容')
    return
  }

  followUpLoading.value = true
  try {
    const payload: Partial<FollowUp> = {
      type: followUpForm.value.type,
      content: followUpForm.value.content,
      next_follow_at: followUpForm.value.next_follow_up_at
        ? new Date(followUpForm.value.next_follow_up_at).toISOString()
        : undefined,
    }
    await addFollowUp(customerId.value, payload)
    message.success('跟进记录已添加')
    followUpVisible.value = false
    await fetchCustomer()
  } catch (err: any) {
    message.error(err.message || '添加跟进记录失败')
  } finally {
    followUpLoading.value = false
  }
}

function handleEditSuccess() {
  fetchCustomer()
}

// --- Lifecycle ---
onMounted(() => {
  fetchCustomer()
})
</script>

<template>
  <div>
    <NPageHeader title="客户详情" @back="goBack">
      <template #footer>
        <NSpace>
          <NButton @click="goBack">返回列表</NButton>
          <NButton type="primary" @click="handleEdit">编辑客户</NButton>
        </NSpace>
      </template>
    </NPageHeader>

    <NCard title="基本信息" style="margin-top: 16px" :loading="loading">
      <template v-if="customer">
        <NDescriptions
          bordered
          :column="3"
          label-placement="left"
        >
          <NDescriptionsItem label="姓名">{{ customer.name }}</NDescriptionsItem>
          <NDescriptionsItem label="手机">{{ customer.phone }}</NDescriptionsItem>
          <NDescriptionsItem label="性别">{{ genderMap[customer.gender || ''] || '-' }}</NDescriptionsItem>
          <NDescriptionsItem label="来源">{{ sourceMap[customer.source || ''] || '-' }}</NDescriptionsItem>
          <NDescriptionsItem label="状态">
            <NTag
              v-if="statusMap[customer.status]"
              :type="statusMap[customer.status].type"
              size="small"
            >
              {{ statusMap[customer.status].label }}
            </NTag>
            <span v-else>{{ customer.status }}</span>
          </NDescriptionsItem>
          <NDescriptionsItem label="预算">{{ formatBudget(customer.budget) }}</NDescriptionsItem>
          <NDescriptionsItem label="婚期">{{ formatDate(customer.wedding_date) }}</NDescriptionsItem>
          <NDescriptionsItem label="负责销售">{{ customer.assigned_user?.name || '-' }}</NDescriptionsItem>
          <NDescriptionsItem label="创建时间">{{ formatDateTime(customer.created_at) }}</NDescriptionsItem>
          <NDescriptionsItem label="备注" :span="3">
            {{ customer.note || '-' }}
          </NDescriptionsItem>
        </NDescriptions>
      </template>
    </NCard>

    <NCard title="跟进记录" style="margin-top: 16px">
      <template #header-extra>
        <NButton type="primary" size="small" @click="handleAddFollowUp">
          新增跟进
        </NButton>
      </template>

      <template v-if="customer?.follow_ups && customer.follow_ups.length > 0">
        <NTimeline>
          <NTimelineItem
            v-for="item in customer.follow_ups"
            :key="item.id"
            :type="item.type === 'visit' ? 'success' : item.type === 'phone' ? 'info' : 'default'"
            :title="followUpTypeLabel[item.type] || item.type"
            :time="formatDateTime(item.created_at)"
          >
            <p>{{ item.content }}</p>
            <p
              v-if="item.next_follow_at"
              style="color: #999; font-size: 12px; margin-top: 4px"
            >
              下次跟进时间：{{ formatDate(item.next_follow_at) }}
            </p>
          </NTimelineItem>
        </NTimeline>
      </template>
      <NEmpty v-else description="暂无跟进记录" />
    </NCard>

    <!-- Edit modal -->
    <CustomerForm
      v-model:visible="editVisible"
      :customer-id="customerId"
      @success="handleEditSuccess"
    />

    <!-- Follow-up modal -->
    <NModal
      v-model:show="followUpVisible"
      preset="card"
      title="新增跟进"
      style="width: 520px"
    >
      <NForm ref="followUpFormRef" label-placement="left" label-width="90">
        <NFormItem label="跟进方式">
          <NSelect
            v-model:value="followUpForm.type"
            :options="followUpTypeOptions"
            placeholder="请选择跟进方式"
          />
        </NFormItem>
        <NFormItem label="跟进内容">
          <NInput
            v-model:value="followUpForm.content"
            type="textarea"
            placeholder="请输入跟进内容"
            :rows="4"
          />
        </NFormItem>
        <NFormItem label="下次跟进">
          <NDatePicker
            v-model:value="followUpForm.next_follow_up_at"
            type="date"
            placeholder="选择下次跟进日期"
            clearable
            style="width: 100%"
          />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="followUpVisible = false">取消</NButton>
          <NButton type="primary" :loading="followUpLoading" @click="submitFollowUp">
            提交
          </NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>
