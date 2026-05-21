<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  NPageHeader,
  NButton,
  NCalendar,
  NCard,
  NSpace,
  NModal,
  NForm,
  NFormItem,
  NInput,
  NDatePicker,
  NTimePicker,
  NSelect,
  NTag,
  NEmpty,
  NList,
  NListItem,
  NThing,
  useMessage,
  type FormInst,
  type FormRules,
  type SelectOption,
} from 'naive-ui'
import { getEvents, createEvent } from '@/api/events'
import type { Event } from '@/api/events'

interface Conflict {
  resource_type: string
  resource_name: string
  event_id: number
  event_title: string
  conflict_start: string
  conflict_end: string
}

const router = useRouter()
const message = useMessage()

// Calendar & events
const selectedDate = ref<number>(Date.now())
const loading = ref(false)
const events = ref<Event[]>([])
const conflicts = ref<Conflict[]>([])

// Sidebar
const showSidebar = ref(false)
const selectedDateEvents = ref<Event[]>([])

// Modal
const showModal = ref(false)
const modalLoading = ref(false)
const formRef = ref<FormInst | null>(null)
const formValue = ref({
  title: '',
  event_date: null as number | null,
  start_time: null as number | null,
  end_time: null as number | null,
  venue_id: null as number | null,
  planner_id: null as number | null,
  remark: '',
})

const venueOptions = ref<SelectOption[]>([])
const plannerOptions = ref<SelectOption[]>([])

const rules: FormRules = {
  title: { required: true, message: '请输入活动名称', trigger: 'blur' },
  event_date: { required: true, type: 'number', message: '请选择活动日期', trigger: 'change' },
  start_time: { required: true, type: 'number', message: '请选择开始时间', trigger: 'change' },
  end_time: { required: true, type: 'number', message: '请选择结束时间', trigger: 'change' },
}

// Status color map
const statusColorMap: Record<string, string> = {
  draft: '#999',
  confirmed: '#18a058',
  executing: '#f0a020',
  completed: '#2080f0',
}

const statusLabelMap: Record<string, string> = {
  draft: '草稿',
  confirmed: '已确认',
  executing: '执行中',
  completed: '已完成',
}

// Group events by date for calendar display
const eventsByDate = computed(() => {
  const map: Record<string, Event[]> = {}
  for (const event of events.value) {
    const date = event.event_date
    if (!map[date]) map[date] = []
    map[date].push(event)
  }
  return map
})

function dateToStr(ts: number): string {
  const d = new Date(ts)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

async function fetchEvents() {
  loading.value = true
  try {
    const now = new Date(selectedDate.value)
    const year = now.getFullYear()
    const month = now.getMonth()
    const startDate = new Date(year, month - 1, 1)
    const endDate = new Date(year, month + 2, 0)
    const res = await getEvents({
      start_date: dateToStr(startDate.getTime()),
      end_date: dateToStr(endDate.getTime()),
      page_size: 200,
    })
    events.value = res.items
  } catch (err: any) {
    message.error(err.message || '获取活动列表失败')
  } finally {
    loading.value = false
  }
}

function handleDateUpdate({ year, month }: { year: number; month: number }) {
  selectedDate.value = new Date(year, month - 1, 1).getTime()
  fetchEvents()
}

function handleDateClick(ts: number) {
  const dateStr = dateToStr(ts)
  selectedDateEvents.value = eventsByDate.value[dateStr] || []
  showSidebar.value = true
}

function handleEventClick(event: Event) {
  router.push(`/events/${event.id}`)
}

function openCreateModal() {
  formValue.value = {
    title: '',
    event_date: null,
    start_time: null,
    end_time: null,
    venue_id: null,
    planner_id: null,
    remark: '',
  }
  conflicts.value = []
  showModal.value = true
}

async function checkConflicts() {
  if (!formValue.value.venue_id || !formValue.value.event_date) return
  try {
    const dateStr = dateToStr(formValue.value.event_date)
    // Fetch all events on the same date to check conflicts client-side
    const res = await getEvents({
      start_date: dateStr,
      end_date: dateStr,
      venue_id: formValue.value.venue_id ?? undefined,
      page_size: 100,
    })
    if (res.items.length > 0) {
      conflicts.value = res.items.map((e) => ({
        resource_type: 'venue',
        resource_name: e.venue?.name || '',
        event_id: e.id,
        event_title: e.title,
        conflict_start: e.start_time,
        conflict_end: e.end_time,
      }))
    } else {
      conflicts.value = []
    }
  } catch {
    // Silently ignore conflict check failures
  }
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  modalLoading.value = true
  try {
    const dateStr = dateToStr(formValue.value.event_date!)
    const startDate = new Date(formValue.value.start_time!)
    const endDate = new Date(formValue.value.end_time!)
    const startStr = `${startDate.getHours().toString().padStart(2, '0')}:${startDate.getMinutes().toString().padStart(2, '0')}`
    const endStr = `${endDate.getHours().toString().padStart(2, '0')}:${endDate.getMinutes().toString().padStart(2, '0')}`

    await createEvent({
      title: formValue.value.title,
      event_date: dateStr,
      start_time: startStr,
      end_time: endStr,
      venue_id: formValue.value.venue_id ?? undefined,
      remark: formValue.value.remark || undefined,
    })
    message.success('活动创建成功')
    showModal.value = false
    fetchEvents()
  } catch (err: any) {
    message.error(err.message || '创建失败')
  } finally {
    modalLoading.value = false
  }
}

onMounted(() => {
  fetchEvents()
})
</script>

<template>
  <div>
    <NPageHeader title="排期管理" @back="() => {}">
      <template #extra>
        <NButton type="primary" @click="openCreateModal">新建活动</NButton>
      </template>
    </NPageHeader>

    <div style="display: flex; gap: 16px; margin-top: 16px;">
      <NCard style="flex: 1;">
        <NCalendar
          v-model:value="selectedDate"
          @update:value="handleDateClick"
          @panel-change="handleDateUpdate"
        >
          <template #date-cell="{ year, month, date }">
            <div v-if="eventsByDate[`${year}-${String(month).padStart(2, '0')}-${String(date).padStart(2, '0')}`]">
              <div
                v-for="event in eventsByDate[`${year}-${String(month).padStart(2, '0')}-${String(date).padStart(2, '0')}`]"
                :key="event.id"
                style="font-size: 12px; padding: 1px 4px; margin: 1px 0; cursor: pointer; display: flex; align-items: center; gap: 4px;"
                @click.stop="handleEventClick(event)"
              >
                <span
                  :style="{
                    display: 'inline-block',
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor: statusColorMap[event.status] || '#999',
                    flexShrink: 0,
                  }"
                />
                <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ event.title }}</span>
              </div>
            </div>
          </template>
        </NCalendar>
      </NCard>

      <NCard
        v-if="showSidebar"
        title="当日活动"
        style="width: 320px; flex-shrink: 0;"
        closable
        @close="showSidebar = false"
      >
        <NEmpty v-if="selectedDateEvents.length === 0" description="当日无活动" />
        <NList v-else>
          <NListItem v-for="event in selectedDateEvents" :key="event.id">
            <NThing>
              <template #header>
                <span style="cursor: pointer; color: #2080f0;" @click="handleEventClick(event)">
                  {{ event.title }}
                </span>
              </template>
              <template #description>
                <NSpace size="small" align="center">
                  <NTag size="small" :bordered="false" :color="{ color: statusColorMap[event.status], textColor: '#fff' }">
                    {{ statusLabelMap[event.status] || event.status }}
                  </NTag>
                  <span style="font-size: 12px; color: #999;">{{ event.start_time }} - {{ event.end_time }}</span>
                </NSpace>
              </template>
            </NThing>
          </NListItem>
        </NList>
      </NCard>
    </div>

    <!-- Create Event Modal -->
    <NModal
      v-model:show="showModal"
      preset="card"
      title="新建活动"
      style="width: 560px;"
      :mask-closable="false"
    >
      <NForm
        ref="formRef"
        :model="formValue"
        :rules="rules"
        label-placement="left"
        label-width="80"
      >
        <NFormItem path="title" label="活动名称">
          <NInput v-model:value="formValue.title" placeholder="请输入活动名称" />
        </NFormItem>
        <NFormItem path="event_date" label="活动日期">
          <NDatePicker
            v-model:value="formValue.event_date"
            type="date"
            style="width: 100%;"
            placeholder="请选择日期"
          />
        </NFormItem>
        <NFormItem path="start_time" label="开始时间">
          <NTimePicker
            v-model:value="formValue.start_time"
            format="HH:mm"
            style="width: 100%;"
            placeholder="请选择开始时间"
          />
        </NFormItem>
        <NFormItem path="end_time" label="结束时间">
          <NTimePicker
            v-model:value="formValue.end_time"
            format="HH:mm"
            style="width: 100%;"
            placeholder="请选择结束时间"
          />
        </NFormItem>
        <NFormItem path="venue_id" label="场地">
          <NSelect
            v-model:value="formValue.venue_id"
            :options="venueOptions"
            placeholder="请选择场地"
            clearable
            @update:value="checkConflicts"
          />
        </NFormItem>
        <NFormItem path="planner_id" label="策划师">
          <NSelect
            v-model:value="formValue.planner_id"
            :options="plannerOptions"
            placeholder="请选择策划师"
            clearable
          />
        </NFormItem>
        <NFormItem path="remark" label="备注">
          <NInput
            v-model:value="formValue.remark"
            type="textarea"
            placeholder="请输入备注"
            :rows="3"
          />
        </NFormItem>
      </NForm>

      <div v-if="conflicts.length > 0" style="margin-top: 12px; padding: 12px; background: #fff7e6; border-radius: 4px; border: 1px solid #ffd591;">
        <div style="font-weight: 600; color: #d48806; margin-bottom: 8px;">场地冲突警告</div>
        <div v-for="c in conflicts" :key="c.event_id" style="font-size: 13px; color: #ad6800;">
          活动「{{ c.event_title }}」已占用该场地 ({{ c.conflict_start }} - {{ c.conflict_end }})
        </div>
      </div>

      <template #action>
        <NSpace justify="end">
          <NButton @click="showModal = false">取消</NButton>
          <NButton type="primary" :loading="modalLoading" @click="handleSubmit">确定</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>
