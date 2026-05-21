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
  NSelect,
  NTag,
  useMessage,
  type DataTableColumns,
  type FormInst,
  type FormRules,
  type SelectOption,
} from 'naive-ui'
import { getUsers, createUser, updateUser, getRoles } from '@/api/users'
import type { User, Role } from '@/api/users'

const message = useMessage()

const loading = ref(false)
const users = ref<User[]>([])
const total = ref(0)
const pagination = reactive({
  page: 1,
  pageSize: 20,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
})

// Roles
const roles = ref<Role[]>([])
const roleOptions = ref<SelectOption[]>([])

const teamOptions: SelectOption[] = [
  { label: '策划部', value: 'planning' },
  { label: '设计部', value: 'design' },
  { label: '执行部', value: 'execution' },
  { label: '销售部', value: 'sales' },
  { label: '行政部', value: 'admin' },
]

const statusOptions: SelectOption[] = [
  { label: '在职', value: 'active' },
  { label: '离职', value: 'inactive' },
  { label: '休假', value: 'leave' },
]

const statusLabelMap: Record<string, string> = {
  active: '在职',
  inactive: '离职',
  leave: '休假',
}

const statusColorMap: Record<string, string> = {
  active: 'success',
  inactive: 'default',
  leave: 'warning',
}

const teamLabelMap: Record<string, string> = {
  planning: '策划部',
  design: '设计部',
  execution: '执行部',
  sales: '销售部',
  admin: '行政部',
}

// Filters
const filters = reactive({
  team: null as string | null,
  status: null as string | null,
  keyword: '',
})

// Modal
const showModal = ref(false)
const modalLoading = ref(false)
const editingUser = ref<User | null>(null)
const formRef = ref<FormInst | null>(null)
const formValue = ref({
  username: '',
  password: '',
  name: '',
  phone: '',
  role_id: null as number | null,
  team: null as string | null,
  status: 'active' as string,
})

const formRules = ref<FormRules>({
  name: { required: true, message: '请输入姓名', trigger: 'blur' },
  phone: { required: true, message: '请输入手机号', trigger: 'blur' },
  status: { required: true, message: '请选择状态', trigger: 'change' },
})

const columns: DataTableColumns<User> = [
  { title: '用户名', key: 'username', width: 120 },
  { title: '姓名', key: 'name', width: 100 },
  { title: '手机', key: 'phone', width: 130 },
  {
    title: '团队',
    key: 'team',
    width: 100,
    render(row) {
      return h(NTag, { size: 'small', type: 'info' }, {
        default: () => teamLabelMap[row.team || ''] || row.team || '-',
      })
    },
  },
  { title: '角色', key: 'role', width: 100 },
  {
    title: '状态',
    key: 'status',
    width: 80,
    render(row) {
      return h(NTag, { type: statusColorMap[row.status] as any, size: 'small' }, {
        default: () => statusLabelMap[row.status] || row.status,
      })
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
        onClick: () => openEditModal(row),
      }, { default: () => '编辑' })
    },
  },
]

async function fetchUsers() {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (filters.team) params.team = filters.team
    if (filters.status) params.status = filters.status
    if (filters.keyword) params.keyword = filters.keyword
    const res = await getUsers(params)
    users.value = res.items
    total.value = res.total
  } catch (err: any) {
    message.error(err.message || '获取员工列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchRoles() {
  try {
    const res = await getRoles()
    roles.value = res
    roleOptions.value = res.map((r) => ({ label: r.display_name || r.name, value: r.id }))
  } catch {
    // Silently handle
  }
}

function handlePageChange(page: number) {
  pagination.page = page
  fetchUsers()
}

function handlePageSizeChange(pageSize: number) {
  pagination.pageSize = pageSize
  pagination.page = 1
  fetchUsers()
}

function handleSearch() {
  pagination.page = 1
  fetchUsers()
}

function openCreateModal() {
  editingUser.value = null
  formValue.value = {
    username: '',
    password: '',
    name: '',
    phone: '',
    role_id: null,
    team: null,
    status: 'active',
  }
  // Add username/password validation for create
  formRules.value = {
    username: { required: true, message: '请输入用户名', trigger: 'blur' },
    password: { required: true, message: '请输入密码', trigger: 'blur' },
    name: { required: true, message: '请输入姓名', trigger: 'blur' },
    phone: { required: true, message: '请输入手机号', trigger: 'blur' },
    status: { required: true, message: '请选择状态', trigger: 'change' },
  }
  showModal.value = true
}

function openEditModal(user: User) {
  editingUser.value = user
  formValue.value = {
    username: user.username,
    password: '',
    name: user.name,
    phone: user.phone || '',
    role_id: null,
    team: (user.team as any) || null,
    status: user.status,
  }
  // No username/password validation for edit
  formRules.value = {
    name: { required: true, message: '请输入姓名', trigger: 'blur' },
    phone: { required: true, message: '请输入手机号', trigger: 'blur' },
    status: { required: true, message: '请选择状态', trigger: 'change' },
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
    if (editingUser.value) {
      const data: any = {
        name: formValue.value.name,
        phone: formValue.value.phone || undefined,
        team: formValue.value.team || undefined,
        status: formValue.value.status,
      }
      if (formValue.value.role_id) data.role_id = formValue.value.role_id
      await updateUser(editingUser.value.id, data)
      message.success('员工信息更新成功')
    } else {
      const data: any = {
        username: formValue.value.username,
        password: formValue.value.password,
        name: formValue.value.name,
        phone: formValue.value.phone || undefined,
        team: formValue.value.team || undefined,
        status: formValue.value.status,
      }
      if (formValue.value.role_id) data.role_id = formValue.value.role_id
      await createUser(data)
      message.success('员工创建成功')
    }
    showModal.value = false
    fetchUsers()
  } catch (err: any) {
    message.error(err.message || '操作失败')
  } finally {
    modalLoading.value = false
  }
}

onMounted(() => {
  fetchUsers()
  fetchRoles()
})
</script>

<template>
  <div>
    <NPageHeader title="员工管理">
      <template #extra>
        <NButton type="primary" @click="openCreateModal">新增员工</NButton>
      </template>
    </NPageHeader>

    <NCard style="margin-top: 16px;">
      <NSpace align="center" style="margin-bottom: 16px;" :wrap="true">
        <NSelect
          v-model:value="filters.team"
          :options="teamOptions"
          placeholder="团队"
          clearable
          style="width: 130px;"
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
          placeholder="搜索姓名/手机"
          clearable
          style="width: 200px;"
          @keyup.enter="handleSearch"
        />
        <NButton type="primary" @click="handleSearch">查询</NButton>
      </NSpace>

      <NDataTable
        :columns="columns"
        :data="users"
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
        :row-key="(row: User) => row.id"
      />
    </NCard>

    <!-- Create/Edit User Modal -->
    <NModal
      v-model:show="showModal"
      preset="card"
      :title="editingUser ? '编辑员工' : '新增员工'"
      style="width: 520px;"
      :mask-closable="false"
    >
      <NForm
        ref="formRef"
        :model="formValue"
        :rules="formRules"
        label-placement="left"
        label-width="80"
      >
        <NFormItem v-if="!editingUser" path="username" label="用户名">
          <NInput v-model:value="formValue.username" placeholder="请输入用户名" />
        </NFormItem>
        <NFormItem v-if="!editingUser" path="password" label="密码">
          <NInput
            v-model:value="formValue.password"
            type="password"
            show-password-on="click"
            placeholder="请输入密码"
          />
        </NFormItem>
        <NFormItem path="name" label="姓名">
          <NInput v-model:value="formValue.name" placeholder="请输入姓名" />
        </NFormItem>
        <NFormItem path="phone" label="手机">
          <NInput v-model:value="formValue.phone" placeholder="请输入手机号" />
        </NFormItem>
        <NFormItem path="role_id" label="角色">
          <NSelect
            v-model:value="formValue.role_id"
            :options="roleOptions"
            placeholder="请选择角色"
            clearable
          />
        </NFormItem>
        <NFormItem path="team" label="团队">
          <NSelect
            v-model:value="formValue.team"
            :options="teamOptions"
            placeholder="请选择团队"
            clearable
          />
        </NFormItem>
        <NFormItem path="status" label="状态">
          <NSelect
            v-model:value="formValue.status"
            :options="statusOptions"
            placeholder="请选择状态"
          />
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
