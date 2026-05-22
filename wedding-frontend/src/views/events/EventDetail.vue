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
  NTag,
  NDataTable,
  NPopconfirm,
  NModal,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NSelect,
  useMessage,
  type DataTableColumns,
  type FormInst,
  type FormRules,
  type SelectOption,
} from 'naive-ui'
import {
  getEvent,
  updateEvent,
  getEventResources,
  addEventResource,
  removeEventResource,
  getStaffSchedule,
} from '@/api/events'
import type { Event, EventResource } from '@/api/events'

const router = useRouter()
const route = useRoute()
const message = useMessage()

const eventId = computed(() => Number(route.params.id))
const loading = ref(false)
const event = ref<Event | null>(null)

// Resources
const resources = ref<EventResource[]>([])
const resourceLoading = ref(false)
const showResourceModal = ref(false)
const resourceFormRef = ref<FormInst | null>(null)
const resourceForm = ref({
  resource_type: '',
  resource_name: '',
  quantity: 1,
  start_time: '',
  end_time: '',
})
const resourceRules: FormRules = {
  resource_type: { required: true, message: '请输入资源类型', trigger: 'blur' },
  resource_name: { required: true, message: '请输入资源名称', trigger: 'blur' },
  quantity: { required: true, type: 'number', message: '请输入数量', trigger: 'change' },
}

// Staff
const staffList = ref<Event[]>([])
const staffLoading = ref(false)

const statusLabelMap: Record<string, string> = {
  draft: '草稿',
  confirmed: '已确认',
  executing: '执行中',
  completed: '已完成',
}

const statusColorMap: Record<string, string> = {
  draft: 'default',
  confirmed: 'success',
  executing: 'warning',
  completed: 'info',
}

// Status transitions
const statusActions: Record<string, { next: string; label: string } | null> = {
  draft: { next: 'confirmed', label: '确认活动' },
  confirmed: { next: 'executing', label: '开始执行' },
  executing: { next: 'completed', label: '标记完成' },
  completed: null,
}

const currentAction = computed(() => {
  if (!event.value) return null
  return statusActions[event.value.status]
})

const resourceColumns: DataTableColumns<EventResource> = [
  { title: '资源类型', key: 'resource_type', width: 120 },
  { title: '资源名称', key: 'resource_name', width: 150 },
  { title: '数量', key: 'quantity', width: 80 },
  { title: '开始时间', key: 'start_time', width: 120 },
  { title: '结束时间', key: 'end_time', width: 120 },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    render(row) {
      return h(
        NPopconfirm,
        { onPositiveClick: () => handleRemoveResource(row.id) },
        {
          trigger: () => h(NButton, { size: 'small', type: 'error', quaternary: true }, { default: () => '移除' }),
          default: () => '确定移除该资源？',
        },
      )
    },
  },
]

async function fetchEvent() {
  loading.value = true
  try {
    event.value = await getEvent(eventId.value)
  } catch (err: any) {
    message.error(err.message || '获取活动详情失败')
  } finally {
    loading.value = false
  }
}

async function fetchResources() {
  resourceLoading.value = true
  try {
    resources.value = await getEventResources(eventId.value)
  } catch {
    // Silently handle
  } finally {
    resourceLoading.value = false
  }
}

async function fetchStaff() {
  staffLoading.value = true
  try {
    staffList.value = await getStaffSchedule({
      date_start: event.value?.event_date,
      date_end: event.value?.event_date,
    })
  } catch {
    // Silently handle
  } finally {
    staffLoading.value = false
  }
}

async function handleStatusChange() {
  if (!currentAction.value || !event.value) return
  try {
    await updateEvent(eventId.value, { status: currentAction.value.next } as Partial<Event>)
    message.success('状态更新成功')
    fetchEvent()
  } catch (err: any) {
    message.error(err.message || '状态更新失败')
  }
}

function openResourceModal() {
  resourceForm.value = {
    resource_type: '',
    resource_name: '',
    quantity: 1,
    start_time: '',
    end_time: '',
  }
  showResourceModal.value = true
}

async function handleAddResource() {
  try {
    await resourceFormRef.value?.validate()
  } catch {
    return
  }
  try {
    await addEventResource(eventId.value, resourceForm.value)
    message.success('资源添加成功')
    showResourceModal.value = false
    fetchResources()
  } catch (err: any) {
    message.error(err.message || '添加资源失败')
  }
}

async function handleRemoveResource(resourceId: number) {
  try {
    await removeEventResource(eventId.value, resourceId)
    message.success('资源已移除')
    fetchResources()
  } catch (err: any) {
    message.error(err.message || '移除资源失败')
  }
}

onMounted(async () => {
  await fetchEvent()
  fetchResources()
  fetchStaff()
})
</script>

<template>
  <div v-if="event">
    <NButton text style="margin-bottom: 16px;" @click="router.push('/events')">
      &lt; 返回排期列表
    </NButton>

    <NPageHeader :title="event.title">
      <template #extra>
        <NSpace>
          <NTag :type="statusColorMap[event.status] as any">
            {{ statusLabelMap[event.status] || event.status }}
          </NTag>
          <NButton
            v-if="currentAction"
            type="primary"
            @click="handleStatusChange"
          >
            {{ currentAction.label }}
          </NButton>
        </NSpace>
      </template>
    </NPageHeader>

    <NCard title="基本信息" style="margin-top: 16px;">
      <NDescriptions bordered :column="3">
        <NDescriptionsItem label="活动日期">{{ event.event_date }}</NDescriptionsItem>
        <NDescriptionsItem label="开始时间">{{ event.start_time }}</NDescriptionsItem>
        <NDescriptionsItem label="结束时间">{{ event.end_time }}</NDescriptionsItem>
        <NDescriptionsItem label="场地">{{ event.venue?.name || '-' }}</NDescriptionsItem>
        <NDescriptionsItem label="状态">
          <NTag :type="statusColorMap[event.status] as any" size="small">
            {{ statusLabelMap[event.status] || event.status }}
          </NTag>
        </NDescriptionsItem>
        <NDescriptionsItem label="备注">{{ event.note || '-' }}</NDescriptionsItem>
      </NDescriptions>
    </NCard>

    <NCard title="资源清单" style="margin-top: 16px;">
      <template #header-extra>
        <NButton type="primary" size="small" @click="openResourceModal">添加资源</NButton>
      </template>
      <NDataTable
        :columns="resourceColumns"
        :data="resources"
        :loading="resourceLoading"
        :bordered="false"
      />
    </NCard>

    <NCard title="人员安排" style="margin-top: 16px;">
      <NDataTable
        :columns="[
          { title: '活动名称', key: 'title' },
          { title: '日期', key: 'event_date' },
          { title: '时间', key: 'start_time' },
          { title: '状态', key: 'status' },
        ]"
        :data="staffList"
        :loading="staffLoading"
        :bordered="false"
      />
    </NCard>

    <!-- Add Resource Modal -->
    <NModal
      v-model:show="showResourceModal"
      preset="card"
      title="添加资源"
      style="width: 480px;"
      :mask-closable="false"
    >
      <NForm
        ref="resourceFormRef"
        :model="resourceForm"
        :rules="resourceRules"
        label-placement="left"
        label-width="80"
      >
        <NFormItem path="resource_type" label="资源类型">
          <NInput v-model:value="resourceForm.resource_type" placeholder="请输入资源类型" />
        </NFormItem>
        <NFormItem path="resource_name" label="资源名称">
          <NInput v-model:value="resourceForm.resource_name" placeholder="请输入资源名称" />
        </NFormItem>
        <NFormItem path="quantity" label="数量">
          <NInputNumber v-model:value="resourceForm.quantity" :min="1" style="width: 100%;" />
        </NFormItem>
        <NFormItem path="start_time" label="开始时间">
          <NInput v-model:value="resourceForm.start_time" placeholder="如 09:00" />
        </NFormItem>
        <NFormItem path="end_time" label="结束时间">
          <NInput v-model:value="resourceForm.end_time" placeholder="如 18:00" />
        </NFormItem>
      </NForm>
      <template #action>
        <NSpace justify="end">
          <NButton @click="showResourceModal = false">取消</NButton>
          <NButton type="primary" @click="handleAddResource">确定</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>
