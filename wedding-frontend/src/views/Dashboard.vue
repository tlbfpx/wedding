<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import {
  NCard,
  NGrid,
  NGi,
  NSpace,
  NSelect,
  NSwitch,
  NAlert,
  useMessage,
} from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import {
  getHealthMetrics,
  getCashflowData,
  getTeamEfficiency,
  getAlerts,
  resolveAlert,
  getDecisionSupport,
  type PeriodType,
  type CompareToType,
  type HealthMetricsResponse,
  type CashflowResponse,
  type TeamEfficiencyResponse,
  type AlertsResponse,
  type DecisionSupportResponse,
} from '@/api/dashboard'
import HealthMetrics from '@/components/dashboard/HealthMetrics.vue'
import CashflowPanel from '@/components/dashboard/CashflowPanel.vue'
import TeamEfficiencyPanel from '@/components/dashboard/TeamEfficiencyPanel.vue'
import AlertsPanel from '@/components/dashboard/AlertsPanel.vue'
import DecisionSupportPanel from '@/components/dashboard/DecisionSupportPanel.vue'

const message = useMessage()
const authStore = useAuthStore()

// ========== 全局筛选器 ==========
const periodOptions = [
  { label: '本月', value: 'month' },
  { label: '本季度', value: 'quarter' },
  { label: '本年', value: 'year' },
]
const selectedPeriod = ref<PeriodType>('month')

const compareToOptions = [
  { label: '环比上月', value: 'prev_period' },
  { label: '同比去年', value: 'same_period_last_year' },
]
const compareTo = ref<CompareToType>('prev_period')

const autoRefresh = ref(true)
const refreshInterval = 5 * 60 * 1000 // 5 minutes
let refreshTimer: ReturnType<typeof setInterval> | null = null

// ========== 权限检查 ==========
const canViewDashboard = computed(() => authStore.hasPermission('dashboard:read') || authStore.hasPermission('dashboard:read_all'))
const canViewFinance = computed(() => authStore.hasPermission('finance:read'))
const canViewDecisionSupport = computed(() => authStore.hasPermission('dashboard:read_all'))

// ========== 数据状态 ==========
const healthLoading = ref(false)
const cashflowLoading = ref(false)
const teamLoading = ref(false)
const alertsLoading = ref(false)
const decisionLoading = ref(false)

const healthData = ref<HealthMetricsResponse | null>(null)
const cashflowData = ref<CashflowResponse | null>(null)
const teamData = ref<TeamEfficiencyResponse | null>(null)
const alertsData = ref<AlertsResponse | null>(null)
const decisionData = ref<DecisionSupportResponse | null>(null)

// ========== 数据加载 ==========
async function fetchHealthMetrics() {
  if (!canViewDashboard.value) return

  healthLoading.value = true
  try {
    const response = await getHealthMetrics({
      period: selectedPeriod.value,
      compare_to: compareTo.value,
    })
    healthData.value = response
  } catch (error) {
    console.error('Failed to fetch health metrics:', error)
    message.error('加载经营健康度数据失败')
  } finally {
    healthLoading.value = false
  }
}

async function fetchCashflowData() {
  if (!canViewDashboard.value || !canViewFinance.value) return

  cashflowLoading.value = true
  try {
    const response = await getCashflowData({
      period: selectedPeriod.value,
    })
    cashflowData.value = response
  } catch (error) {
    console.error('Failed to fetch cashflow data:', error)
    message.error('加载现金流数据失败')
  } finally {
    cashflowLoading.value = false
  }
}

async function fetchTeamEfficiency() {
  if (!canViewDashboard.value) return

  teamLoading.value = true
  try {
    const response = await getTeamEfficiency({
      period: selectedPeriod.value,
      page: 1,
      page_size: 20,
    })
    teamData.value = response
  } catch (error) {
    console.error('Failed to fetch team efficiency:', error)
    message.error('加载团队效能数据失败')
  } finally {
    teamLoading.value = false
  }
}

async function fetchAlerts() {
  if (!canViewDashboard.value) return

  alertsLoading.value = true
  try {
    const response = await getAlerts({
      level: 'all',
      limit: 20,
    })
    alertsData.value = response
  } catch (error) {
    console.error('Failed to fetch alerts:', error)
    message.error('加载风险预警失败')
  } finally {
    alertsLoading.value = false
  }
}

async function fetchDecisionSupport() {
  if (!canViewDecisionSupport.value) return

  decisionLoading.value = true
  try {
    const response = await getDecisionSupport({
      period: selectedPeriod.value,
      dimension: 'source',
    })
    decisionData.value = response
  } catch (error) {
    console.error('Failed to fetch decision support:', error)
    message.error('加载决策支撑数据失败')
  } finally {
    decisionLoading.value = false
  }
}

async function fetchAllData() {
  // 并行请求所有模块数据
  await Promise.allSettled([
    fetchHealthMetrics(),
    fetchCashflowData(),
    fetchTeamEfficiency(),
    fetchAlerts(),
    fetchDecisionSupport(),
  ])
}

// ========== 自动刷新 ==========
function startAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  if (autoRefresh.value) {
    refreshTimer = setInterval(() => {
      fetchAllData()
    }, refreshInterval)
  }
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

watch(autoRefresh, () => {
  if (autoRefresh.value) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
})

// ========== 周期切换 ==========
watch([selectedPeriod, compareTo], () => {
  fetchAllData()
})

// ========== 预警处理 ==========
async function handleAlertResolved(alertId: string) {
  // 重新加载预警列表
  await fetchAlerts()
  message.success('预警已标记为已处理')
}

// ========== 生命周期 ==========
onMounted(() => {
  if (!canViewDashboard.value) {
    message.warning('您没有查看工作台的权限')
    return
  }
  fetchAllData()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<template>
  <div>
    <!-- 权限检查 -->
    <NAlert v-if="!canViewDashboard" type="warning" style="margin-bottom: 16px">
      您没有查看工作台的权限，请联系管理员
    </NAlert>

    <template v-else>
      <!-- 顶部全局筛选器 -->
      <NCard style="margin-bottom: 16px">
        <NSpace justify="space-between" align="center">
          <NSpace>
            <span style="font-size: 14px; color: #666">统计周期</span>
            <NSelect
              v-model:value="selectedPeriod"
              :options="periodOptions"
              style="width: 120px"
            />
            <NSelect
              v-model:value="compareTo"
              :options="compareToOptions"
              style="width: 120px"
            />
          </NSpace>
          <NSpace align="center">
            <span style="font-size: 14px; color: #666">自动刷新</span>
            <NSwitch v-model:value="autoRefresh" />
          </NSpace>
        </NSpace>
      </NCard>

      <!-- 核心卡片区：经营健康度 -->
      <HealthMetrics
        :loading="healthLoading"
        :metrics="healthData?.metrics"
        style="margin-bottom: 16px"
      />

      <!-- 第二行：现金流 + 团队效能 -->
      <NGrid :x-gap="16" :y-gap="16" :cols="2" style="margin-bottom: 16px" responsive="screen">
        <NGi v-if="canViewFinance">
          <CashflowPanel
            :loading="cashflowLoading"
            :data="cashflowData"
          />
        </NGi>
        <NGi>
          <TeamEfficiencyPanel
            :loading="teamLoading"
            :data="teamData"
          />
        </NGi>
      </NGrid>

      <!-- 第三行：风险预警 -->
      <AlertsPanel
        :loading="alertsLoading"
        :data="alertsData"
        @resolved="handleAlertResolved"
        style="margin-bottom: 16px"
      />

      <!-- 第四行：决策支撑 -->
      <DecisionSupportPanel
        v-if="canViewDecisionSupport"
        :loading="decisionLoading"
        :data="decisionData"
      />
    </template>
  </div>
</template>
