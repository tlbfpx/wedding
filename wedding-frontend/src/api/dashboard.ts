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
