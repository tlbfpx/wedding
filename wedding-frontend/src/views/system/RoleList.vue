<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  NPageHeader,
  NButton,
  NCard,
  NSpace,
  NTag,
  NSwitch,
  useMessage,
} from 'naive-ui'
import { getRoles, updateRole } from '@/api/users'
import type { Role } from '@/api/users'

const message = useMessage()

const loading = ref(false)
const roles = ref<Role[]>([])

// Permission modules and actions
const modules = [
  { key: 'customers', label: '客户管理' },
  { key: 'events', label: '排期管理' },
  { key: 'orders', label: '订单管理' },
  { key: 'suppliers', label: '供应商管理' },
  { key: 'venues', label: '场地管理' },
  { key: 'users', label: '员工管理' },
  { key: 'roles', label: '角色权限' },
  { key: 'finance', label: '财务管理' },
  { key: 'reports', label: '报表统计' },
  { key: 'system', label: '系统设置' },
]

const actions = [
  { key: 'read', label: '读取' },
  { key: 'write', label: '写入' },
]

// Track local permission state for editing
const localPermissions = ref<Record<number, Record<string, boolean>>>({})

function hasPermission(role: Role, module: string, action: string): boolean {
  const permKey = `${module}:${action}`
  return role.permissions.includes(permKey)
}

function getLocalPermission(roleId: number, module: string, action: string): boolean {
  const key = `${module}:${action}`
  if (localPermissions.value[roleId] && key in localPermissions.value[roleId]) {
    return localPermissions.value[roleId][key]
  }
  const role = roles.value.find((r) => r.id === roleId)
  return role ? role.permissions.includes(key) : false
}

function togglePermission(roleId: number, module: string, action: string, value: boolean) {
  if (!localPermissions.value[roleId]) {
    localPermissions.value[roleId] = {}
  }
  const key = `${module}:${action}`
  localPermissions.value[roleId][key] = value
}

async function fetchRoles() {
  loading.value = true
  try {
    roles.value = await getRoles()
    // Initialize local permissions from loaded roles
    localPermissions.value = {}
  } catch (err: any) {
    message.error(err.message || '获取角色列表失败')
  } finally {
    loading.value = false
  }
}

async function handleSave(role: Role) {
  const roleId = role.id
  const currentPerms = { ...localPermissions.value[roleId] }

  // Build the permissions array from local state
  const permissions: string[] = []
  for (const mod of modules) {
    for (const act of actions) {
      const key = `${mod.key}:${act.key}`
      if (currentPerms[key] === true || (!currentPerms.hasOwnProperty(key) && role.permissions.includes(key))) {
        permissions.push(key)
      }
    }
  }

  try {
    await updateRole(roleId, { permissions })
    message.success(`角色「${role.display_name || role.name}」权限更新成功`)
    // Clean up local overrides after save
    delete localPermissions.value[roleId]
    fetchRoles()
  } catch (err: any) {
    message.error(err.message || '权限更新失败')
  }
}

onMounted(() => {
  fetchRoles()
})
</script>

<template>
  <div>
    <NPageHeader title="角色权限" />

    <NSpace vertical :size="16" style="margin-top: 16px;">
      <NCard v-for="role in roles" :key="role.id" :title="role.display_name || role.name">
        <template #header-extra>
          <NButton type="primary" size="small" @click="handleSave(role)">保存</NButton>
        </template>

        <table style="width: 100%; border-collapse: collapse;">
          <thead>
            <tr>
              <th style="text-align: left; padding: 8px 12px; border-bottom: 1px solid #efeff5; width: 160px;">
                模块
              </th>
              <th
                v-for="action in actions"
                :key="action.key"
                style="text-align: center; padding: 8px 12px; border-bottom: 1px solid #efeff5; width: 120px;"
              >
                {{ action.label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="mod in modules" :key="mod.key">
              <td style="padding: 8px 12px; border-bottom: 1px solid #f9f9fc;">
                {{ mod.label }}
              </td>
              <td
                v-for="action in actions"
                :key="action.key"
                style="text-align: center; padding: 8px 12px; border-bottom: 1px solid #f9f9fc;"
              >
                <NSwitch
                  :value="getLocalPermission(role.id, mod.key, action.key)"
                  @update:value="(val: boolean) => togglePermission(role.id, mod.key, action.key, val)"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </NCard>
    </NSpace>
  </div>
</template>
