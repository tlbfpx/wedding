<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
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
  NInputNumber,
  NDatePicker,
  NTag,
  useMessage,
  type DataTableColumns,
  type FormInst,
  type FormRules,
} from 'naive-ui'
import { getEvents } from '@/api/events'
import type { Event } from '@/api/events'
import request from '@/api/index'

interface Venue {
  id: number
  name: string
  address?: string
  capacity?: number
  contact?: string
  phone?: string
  price?: number
  note?: string
}

interface VenueListParams {
  page?: number
  page_size?: number
  keyword?: string
  capacity_min?: number
}

const message = useMessage()

const loading = ref(false)
const venues = ref<Venue[]>([])
const total = ref(0)
const pagination = reactive({
  page: 1,
  pageSize: 20,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
})

// Filters
const filters = reactive({
  keyword: '',
  capacity_min: null as number | null,
})

// Modal
const showModal = ref(false)
const modalLoading = ref(false)
const editingVenue = ref<Venue | null>(null)
const formRef = ref<FormInst | null>(null)
const formValue = ref({
  name: '',
  address: '',
  capacity: null as number | null,
  contact: '',
  phone: '',
  price: null as number | null,
  note: '',
})

const formRules: FormRules = {
  name: { required: true, message: '请输入场地名称', trigger: 'blur' },
}

// Schedule modal
const showScheduleModal = ref(false)
const scheduleVenue = ref<Venue | null>(null)
const scheduleEvents = ref<Event[]>([])
const scheduleRange = ref<[number, number] | null>(null)

const columns: DataTableColumns<Venue> = [
  { title: '名称', key: 'name', width: 140 },
  { title: '地址', key: 'address', width: 200, ellipsis: { tooltip: true } },
  { title: '容纳人数', key: 'capacity', width: 100 },
  { title: '联系人', key: 'contact', width: 100 },
  { title: '电话', key: 'phone', width: 130 },
  {
    title: '参考价格',
    key: 'price',
    width: 120,
    render(row) {
      return row.price != null ? `¥${row.price.toLocaleString()}` : '-'
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    render(row) {
      return h(NSpace, { size: 'small' }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, onClick: () => openScheduleModal(row) }, { default: () => '查看档期' }),
          h(NButton, { size: 'small', quaternary: true, onClick: () => openEditModal(row) }, { default: () => '编辑' }),
        ],
      })
    },
  },
]

async function fetchVenues() {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.capacity_min) params.capacity_min = filters.capacity_min
    const res = await request.get('/venues', { params })
    venues.value = res.items
    total.value = res.total
  } catch (err: any) {
    message.error(err.message || '获取场地列表失败')
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  pagination.page = page
  fetchVenues()
}

function handlePageSizeChange(pageSize: number) {
  pagination.pageSize = pageSize
  pagination.page = 1
  fetchVenues()
}

function handleSearch() {
  pagination.page = 1
  fetchVenues()
}

function openCreateModal() {
  editingVenue.value = null
  formValue.value = {
    name: '',
    address: '',
    capacity: null,
    contact: '',
    phone: '',
    price: null,
    note: '',
  }
  showModal.value = true
}

function openEditModal(venue: Venue) {
  editingVenue.value = venue
  formValue.value = {
    name: venue.name,
    address: venue.address || '',
    capacity: venue.capacity ?? null,
    contact: venue.contact || '',
    phone: venue.phone || '',
    price: venue.price ?? null,
    note: venue.note || '',
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
      address: formValue.value.address || undefined,
      capacity: formValue.value.capacity ?? undefined,
      contact: formValue.value.contact || undefined,
      phone: formValue.value.phone || undefined,
      price: formValue.value.price ?? undefined,
      note: formValue.value.note || undefined,
    }
    if (editingVenue.value) {
      await request.put(`/venues/${editingVenue.value.id}`, data)
      message.success('场地更新成功')
    } else {
      await request.post('/venues', data)
      message.success('场地创建成功')
    }
    showModal.value = false
    fetchVenues()
  } catch (err: any) {
    message.error(err.message || '操作失败')
  } finally {
    modalLoading.value = false
  }
}

async function openScheduleModal(venue: Venue) {
  scheduleVenue.value = venue
  showScheduleModal.value = true
  scheduleRange.value = null
  scheduleEvents.value = []
}

async function fetchSchedule() {
  if (!scheduleRange.value || !scheduleVenue.value) return
  try {
    const [start, end] = scheduleRange.value
    const startStr = new Date(start).toISOString().slice(0, 10)
    const endStr = new Date(end).toISOString().slice(0, 10)
    const res = await getEvents({
      start_date: startStr,
      end_date: endStr,
      venue_id: scheduleVenue.value.id,
      page_size: 100,
    })
    scheduleEvents.value = res.items
  } catch (err: any) {
    message.error(err.message || '获取档期失败')
  }
}

function handleScheduleRangeChange(val: [number, number] | null) {
  scheduleRange.value = val
  if (val) fetchSchedule()
}

onMounted(() => {
  fetchVenues()
})
</script>

<template>
  <div>
    <NPageHeader title="场地管理">
      <template #extra>
        <NButton type="primary" @click="openCreateModal">新增场地</NButton>
      </template>
    </NPageHeader>

    <NCard style="margin-top: 16px;">
      <NSpace align="center" style="margin-bottom: 16px;">
        <NInput
          v-model:value="filters.keyword"
          placeholder="搜索场地名称/地址"
          clearable
          style="width: 240px;"
          @keyup.enter="handleSearch"
        />
        <NInputNumber
          v-model:value="filters.capacity_min"
          placeholder="最小容纳人数"
          clearable
          style="width: 180px;"
        />
        <NButton type="primary" @click="handleSearch">查询</NButton>
      </NSpace>

      <NDataTable
        :columns="columns"
        :data="venues"
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
        :row-key="(row: Venue) => row.id"
      />
    </NCard>

    <!-- Create/Edit Venue Modal -->
    <NModal
      v-model:show="showModal"
      preset="card"
      :title="editingVenue ? '编辑场地' : '新增场地'"
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
        <NFormItem path="name" label="场地名称">
          <NInput v-model:value="formValue.name" placeholder="请输入场地名称" />
        </NFormItem>
        <NFormItem path="address" label="地址">
          <NInput v-model:value="formValue.address" placeholder="请输入地址" />
        </NFormItem>
        <NFormItem path="capacity" label="容纳人数">
          <NInputNumber v-model:value="formValue.capacity" :min="1" style="width: 100%;" placeholder="请输入容纳人数" />
        </NFormItem>
        <NFormItem path="contact" label="联系人">
          <NInput v-model:value="formValue.contact" placeholder="请输入联系人" />
        </NFormItem>
        <NFormItem path="phone" label="电话">
          <NInput v-model:value="formValue.phone" placeholder="请输入联系电话" />
        </NFormItem>
        <NFormItem path="price" label="参考价格">
          <NInputNumber v-model:value="formValue.price" :min="0" style="width: 100%;" placeholder="请输入参考价格">
            <template #prefix>¥</template>
          </NInputNumber>
        </NFormItem>
        <NFormItem path="note" label="备注">
          <NInput v-model:value="formValue.note" type="textarea" placeholder="请输入备注" :rows="3" />
        </NFormItem>
      </NForm>
      <template #action>
        <NSpace justify="end">
          <NButton @click="showModal = false">取消</NButton>
          <NButton type="primary" :loading="modalLoading" @click="handleSubmit">确定</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- Schedule Modal -->
    <NModal
      v-model:show="showScheduleModal"
      preset="card"
      :title="`${scheduleVenue?.name || ''} - 档期查询`"
      style="width: 640px;"
    >
      <NDatePicker
        type="daterange"
        clearable
        style="width: 100%; margin-bottom: 16px;"
        @update:value="handleScheduleRangeChange"
      />
      <NDataTable
        v-if="scheduleEvents.length > 0"
        :columns="[
          { title: '活动名称', key: 'title' },
          { title: '日期', key: 'event_date' },
          { title: '时间', key: 'start_time' },
          { title: '状态', key: 'status' },
        ]"
        :data="scheduleEvents"
        :bordered="false"
        size="small"
      />
      <div v-else-if="scheduleRange" style="text-align: center; color: #999; padding: 24px 0;">
        该时段暂无排期
      </div>
      <div v-else style="text-align: center; color: #999; padding: 24px 0;">
        请选择日期范围查看档期
      </div>
    </NModal>
  </div>
</template>
