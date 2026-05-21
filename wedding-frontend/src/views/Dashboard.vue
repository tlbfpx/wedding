<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  NCard,
  NGrid,
  NGi,
  NStatistic,
  NSkeleton,
  NSpace,
  NList,
  NListItem,
  NThing,
  NTag,
} from 'naive-ui'
import { getOverview } from '@/api/dashboard'
import { getEvents as getEventList } from '@/api/events'
import type { OverviewData } from '@/api/dashboard'
import type { Event } from '@/api/events'

const loading = ref(true)
const overview = ref<OverviewData | null>(null)
const recentEvents = ref<Event[]>([])

const todos = ref([
  { title: '跟进新客户 张先生', type: 'warning' },
  { title: '确认场地预订 - 5月25日', type: 'info' },
  { title: '审核供应商报价单', type: 'error' },
  { title: '安排下周排期', type: 'default' },
])

onMounted(async () => {
  try {
    const [overviewData, eventsData] = await Promise.allSettled([
      getOverview(),
      getEventList({ page_size: 5 }),
    ])
    if (overviewData.status === 'fulfilled') {
      overview.value = overviewData.value
    }
    if (eventsData.status === 'fulfilled') {
      recentEvents.value = eventsData.value.items
    }
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <NGrid :x-gap="16" :y-gap="16" :cols="4">
      <NGi>
        <NCard>
          <NSkeleton v-if="loading" text :repeat="2" />
          <NStatistic v-else label="本月订单" :value="overview?.month_orders ?? 0">
            <template #suffix>单</template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NSkeleton v-if="loading" text :repeat="2" />
          <NStatistic v-else label="营业额" :value="overview?.month_revenue ?? 0">
            <template #prefix>¥</template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NSkeleton v-if="loading" text :repeat="2" />
          <NStatistic v-else label="待跟进客户" :value="overview?.pending_customers ?? 0">
            <template #suffix>人</template>
          </NStatistic>
        </NCard>
      </NGi>
      <NGi>
        <NCard>
          <NSkeleton v-if="loading" text :repeat="2" />
          <NStatistic v-else label="本月排期" :value="overview?.month_events ?? 0">
            <template #suffix>场</template>
          </NStatistic>
        </NCard>
      </NGi>
    </NGrid>

    <NGrid :x-gap="16" :y-gap="16" :cols="2" style="margin-top: 16px">
      <NGi>
        <NCard title="待办事项">
          <NList>
            <NListItem v-for="(todo, index) in todos" :key="index">
              <NThing :title="todo.title" />
              <template #suffix>
                <NTag :type="todo.type as any" size="small">待处理</NTag>
              </template>
            </NListItem>
          </NList>
        </NCard>
      </NGi>
      <NGi>
        <NCard title="近期排期">
          <NSkeleton v-if="loading" text :repeat="4" />
          <NList v-else>
            <NListItem v-for="event in recentEvents" :key="event.id">
              <NThing :title="event.title">
                <template #description>
                  <NSpace size="small">
                    <NTag size="small">{{ event.event_date }}</NTag>
                    <NTag size="small" type="info">{{ event.status }}</NTag>
                  </NSpace>
                </template>
              </NThing>
            </NListItem>
            <NListItem v-if="recentEvents.length === 0">
              <NThing title="暂无排期" />
            </NListItem>
          </NList>
        </NCard>
      </NGi>
    </NGrid>
  </div>
</template>
