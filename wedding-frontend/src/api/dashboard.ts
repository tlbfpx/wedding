import request from './index'

export interface OverviewData {
  period: string
  customers: {
    total: number
    by_status: Record<string, number>
  }
  orders: {
    count: number
    total_amount: number
    paid_amount: number
  }
  upcoming_events: number
}

export interface SalesRankingItem {
  sale_id: number
  sale_name: string
  order_count: number
  total_amount: number
}

export interface SalesRankingResult {
  period: string
  ranking: SalesRankingItem[]
}

export interface ConversionFunnel {
  funnel: Array<{ status: string; count: number }>
}

export interface FinanceSummary {
  period: string
  order_count: number
  total_amount: number
  total_paid: number
  receivable: number
  payment_method_breakdown: Record<string, number>
}

export interface ScheduleHeatmapResult {
  month: string
  heatmap: Array<{ date: string; count: number }>
}

export interface SupplierRankingItem {
  supplier_id: number
  supplier_name: string
  type: string
  rating: number
  evaluation_count: number
}

export interface SupplierRankingResult {
  ranking: SupplierRankingItem[]
}

// ============ v1 API Types (管理层驾驶舱) ============

export type PeriodType = 'month' | 'quarter' | 'year'
export type CompareToType = 'prev_period' | 'same_period_last_year'
export type AlertLevel = 'high' | 'medium' | 'low'
export type DecisionDimension = 'source' | 'service' | 'supplier'

export interface MetricValue {
  value: number
  trend?: number  // 增长率（正数增长，负数下降）
  target?: number
  achievement?: number  // 达成率
}

export interface HealthMetricsResponse {
  period: string
  period_start: string
  period_end: string
  compare_period_start?: string
  compare_period_end?: string
  metrics: {
    revenue: MetricValue
    orders: MetricValue
    avg_order_value: MetricValue
    sign_rate: MetricValue
    gross_profit: MetricValue
  }
}

export interface CashflowResponse {
  period: string
  period_start: string
  period_end: string
  cash_in: {
    total: number
    by_method: Record<string, number>
  }
  receivables: {
    total: number
    overdue: number
    overdue_count: number
  }
  aging: Array<{
    bucket: string
    amount: number
    percent: number
  }>
  turnover_days: number
  payments: {
    total: number
    paid: number
    pending: number
  }
}

export interface TeamEfficiencyResponse {
  period: string
  period_start: string
  period_end: string
  teams: Array<{
    team: string
    total_revenue: number
    headcount: number
    avg_revenue: number
  }>
  funnel: Array<{
    stage: string
    count: number
    rate: number
  }>
  new_customers: number
  follow_up_count: number
  ranking: Array<{
    rank: number
    sale_id: number
    sale_name: string
    team: string
    order_count: number
    revenue: number
    avg_order_value: number
    conversion_rate: number
    follow_up_count: number
  }>
  total: number
  page: number
  page_size: number
}

export interface AlertItem {
  id: string
  level: AlertLevel
  type: string
  title: string
  detail: string
  entity_type: string
  entity_id: number
  owner_id?: number
  owner_name?: string
  actions: string[]
  created_at: string
}

export interface AlertsResponse {
  high_count: number
  medium_count: number
  low_count: number
  alerts: AlertItem[]
  total: number
}

export interface DecisionSupportResponse {
  period: string
  period_start: string
  period_end: string
  source_roi: Array<{
    source: string
    source_id: number
    lead_count: number
    signed_count: number
    conversion_rate: number
    revenue: number
    avg_order_value: number
    roi_score: number  // 1-5 stars
  }>
  service_breakdown: Array<{
    service_type: string
    revenue: number
    percent: number
    count: number
  }>
  supplier_value: Array<{
    supplier_id: number
    supplier_name: string
    type: string
    cooperation_count: number
    total_amount: number
    avg_rating: number
    value_score: number
  }>
}

export interface ResolveAlertResponse {
  success: boolean
  resolved_at: string
}

// ============ v0 API Functions (保留向后兼容) ============

export function getOverview(params?: { period?: string }): Promise<OverviewData> {
  return request.get('/dashboard/overview', { params })
}

export function getSalesRanking(params?: { period?: string; team?: string }): Promise<SalesRankingResult> {
  return request.get('/dashboard/sales-ranking', { params })
}

export function getConversionFunnel(params?: { date_start?: string; date_end?: string }): Promise<ConversionFunnel> {
  return request.get('/dashboard/conversion-funnel', { params })
}

export function getFinanceSummary(params?: { period?: string }): Promise<FinanceSummary> {
  return request.get('/dashboard/finance-summary', { params })
}

export function getScheduleHeatmap(params: { month: string }): Promise<ScheduleHeatmapResult> {
  return request.get('/dashboard/schedule-heatmap', { params })
}

export function getSupplierRanking(params?: { type?: string }): Promise<SupplierRankingResult> {
  return request.get('/dashboard/supplier-ranking', { params })
}

// ============ v1 API Functions (管理层驾驶舱) ============

/**
 * 获取经营健康度数据
 */
export function getHealthMetrics(params: {
  period: PeriodType
  compare_to?: CompareToType
}): Promise<HealthMetricsResponse> {
  return request.get('/v1/dashboard/health', { params })
}

/**
 * 获取现金流与应收数据
 */
export function getCashflowData(params: {
  period: PeriodType
}): Promise<CashflowResponse> {
  return request.get('/v1/dashboard/cashflow', { params })
}

/**
 * 获取团队效能数据
 */
export function getTeamEfficiency(params: {
  period: PeriodType
  team?: string
  page?: number
  page_size?: number
}): Promise<TeamEfficiencyResponse> {
  return request.get('/v1/dashboard/team-efficiency', { params })
}

/**
 * 获取风险预警列表
 */
export function getAlerts(params?: {
  level?: AlertLevel | 'all'
  type?: string
  limit?: number
  offset?: number
}): Promise<AlertsResponse> {
  return request.get('/v1/dashboard/alerts', { params })
}

/**
 * 标记预警已处理
 */
export function resolveAlert(alertId: string, data?: { note?: string }): Promise<ResolveAlertResponse> {
  return request.post(`/v1/dashboard/alerts/${alertId}/resolve`, data)
}

/**
 * 获取决策支撑数据
 */
export function getDecisionSupport(params: {
  period: PeriodType
  dimension?: DecisionDimension
}): Promise<DecisionSupportResponse> {
  return request.get('/v1/dashboard/decision-support', { params })
}
