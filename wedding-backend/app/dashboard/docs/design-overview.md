# Dashboard 模块 - 设计概览

> 模块路径: `app/dashboard`
> API 前缀: `/api/v1/dashboard`
> 版本: v2.0
> 创建日期: 2026-06-04

---

## 1. 模块职责

Dashboard 模块负责管理层驾驶舱的数据聚合与呈现，提供经营健康度、现金流分析、团队效能、风险预警、决策支撑五大维度的数据洞察。

### 1.1 核心功能

1. **经营健康度分析** — 营收、订单、客单价、签约率、毛利等核心指标，支持趋势对比和目标达成
2. **现金流与应收管理** — 现金流入、应收余额、逾期应收、账龄分析、周转天数
3. **团队效能分析** — 人均产出、转化漏斗、销售排行、团队对比
4. **风险预警监控** — 逾期应收、即将到期活动、长期未跟进客户等风险预警
5. **决策支撑数据** — 客户来源 ROI、服务类型收入占比、供应商性价比分析

### 1.2 边界界定

**属于本模块:**
- 跨领域数据的聚合与计算
- 多维度统计指标的生成
- 预警规则的判断与预警生成
- 缓存策略的管理
- 权限范围内的数据过滤

**不属于本模块:**
- 订单/客户/供应商的 CRUD（由对应业务模块负责）
- 财务应收/收款的详细管理（由 Finance 模块负责）
- 通用权限验证（由 `require_permission` 中间件负责）
- 文件上传/通用工具（由基础设施层负责）

---

## 2. 现状问题分析

### 2.1 当前架构问题

| 问题 | 影响 | 改进方向 |
|------|------|----------|
| **单文件路由** | 所有查询逻辑内联在 `dashboard.py`，可维护性差 | 拆分为 Service 层 |
| **缺少领域模型** | 查询逻辑分散，无统一的数据结构 | 引入 DTO/VO 对象 |
| **无缓存策略** | 仅 overview 有简单缓存，未统一管理 | 建立分层缓存策略 |
| **权限过滤简陋** | 依赖前端传参，后端未按 scope 过滤 | 结合 `require_permission` 的 scope 过滤 |
| **缺少数据聚合层** | 直接查询 Model，聚合逻辑复杂 | 引入 Application Service 聚合 |

### 2.2 现有 API 兼容性

```
/api/dashboard/overview          → 废弃，替换为 /health
/api/dashboard/sales-ranking     → 废弃，整合到 /team-efficiency
/api/dashboard/conversion-funnel → 废弃，整合到 /team-efficiency
/api/dashboard/finance-summary   → 废弃，替换为 /cashflow
/api/dashboard/schedule-heatmap  → 保留
/api/dashboard/supplier-ranking  → 保留
```

旧 API 保持可用，添加 `Deprecation: true` 响应头。

---

## 3. 领域模型

### 3.1 值对象（Value Objects）

#### PeriodRange（时间范围）

```python
@dataclass
class PeriodRange:
    """统计周期范围"""
    period: PeriodType  # month/quarter/year
    start: datetime
    end: datetime
    compare_start: Optional[datetime] = None  # 对比周期起始
    compare_end: Optional[datetime] = None
```

#### MetricValue（指标值）

```python
@dataclass
class MetricValue:
    """通用指标值（含趋势）"""
    value: Decimal
    trend: Optional[float] = None  # 环比/同比增长率
    target: Optional[Decimal] = None  # 目标值
    achievement: Optional[float] = None  # 达成率
```

#### AlertLevel（预警级别）

```python
class AlertLevel(str, enum.Enum):
    high = "high"      # 高风险（红色）
    medium = "medium"  # 中风险（黄色）
    low = "low"        # 低风险（蓝色）
```

### 3.2 DTO（Data Transfer Objects）

#### HealthMetrics（经营健康度指标）

```python
@dataclass
class HealthMetrics:
    """经营健康度响应"""
    period: PeriodType
    period_start: date
    period_end: date
    metrics: dict[str, MetricValue]  # revenue/orders/avg_order_value/sign_rate/gross_profit
```

#### CashflowMetrics（现金流指标）

```python
@dataclass
class CashflowMetrics:
    """现金流与应收响应"""
    period: PeriodType
    cash_in: CashInBreakdown
    receivables: ReceivablesSummary
    aging: list[AgingBucket]
    turnover_days: int
    payments: PaymentSummary
```

#### TeamEfficiencyMetrics（团队效能指标）

```python
@dataclass
class TeamEfficiencyMetrics:
    """团队效能响应"""
    period: PeriodType
    teams: list[TeamStats]
    funnel: list[FunnelStage]
    new_customers: int
    follow_up_count: int
    ranking: list[SalesRankingItem]
```

#### AlertItem（预警项）

```python
@dataclass
class AlertItem:
    """预警项"""
    id: str
    level: AlertLevel
    type: str  # overdue_receivable/upcoming_event/long_no_follow/etc.
    title: str
    detail: str
    entity_type: str  # order/customer/event/supplier
    entity_id: int
    owner_id: Optional[int]
    owner_name: Optional[str]
    actions: list[str]  # view_detail/mark_resolved/send_remind
    created_at: datetime
```

---

## 4. 模块分层设计

### 4.1 分层架构

```
┌─────────────────────────────────────────────────────────┐
│                     Interfaces Layer                      │
│  ┌───────────────────────────────────────────────────┐   │
│  │  Controllers (HTTP API)                            │   │
│  │  - HealthController        → /health               │   │
│  │  - CashflowController      → /cashflow             │   │
│  │  - TeamEfficiencyController → /team-efficiency    │   │
│  │  - AlertsController         → /alerts               │   │
│  │  - DecisionController       → /decision-support     │   │
│  │  - LegacyController         → /overview (deprecated)│   │
│  └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                       │
│  ┌───────────────────────────────────────────────────┐   │
│  │  Services (Use Case Orchestration)                  │   │
│  │  - HealthService              → 聚合经营健康度数据   │   │
│  │  - CashflowService            → 聚合现金流数据       │   │
│  │  - TeamEfficiencyService      → 聚合团队效能数据   │   │
│  │  - AlertService               → 生成预警列表        │   │
│  │  - DecisionSupportService     → 聚合决策支撑数据   │   │
│  └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│                      Domain Layer                         │
│  ┌───────────────────────────────────────────────────┐   │
│  │  Value Objects & DTOs                               │   │
│  │  - PeriodRange, MetricValue, AlertLevel            │   │
│  │  - HealthMetrics, CashflowMetrics, etc.            │   │
│  └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                           ▲
┌─────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                     │
│  ┌───────────────────────────────────────────────────┐   │
│  │  Repositories (Data Access)                         │   │
│  │  - 注: Dashboard 不直接操作仓储，通过 Model 查询    │   │
│  │  Cache Provider                                       │   │
│  │  - RedisCacheService                                 │   │
│  └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 4.2 目录结构

```
app/dashboard/
├── __init__.py
├── docs/
│   ├── contracts.md              # 接口契约文档
│   ├── design-overview.md        # 设计概览（本文件）
│   ├── feature-health-metrics.md # 经营健康度功能详设
│   ├── feature-cashflow.md       # 现金流功能详设
│   ├── feature-team-efficiency.md# 团队效能功能详设
│   ├── feature-alerts.md         # 风险预警功能详设
│   ├── feature-decision-support.md# 决策支撑功能详设
│   └── changelogs/               # 变更日志
│       └── 2026-06-04-dashboard-redesign.md
├── domain/
│   ├── __init__.py
│   ├── value_objects/
│   │   ├── __init__.py
│   │   ├── period_range.py
│   │   ├── metric_value.py
│   │   ├── alert_level.py
│   │   └── enums.py
│   └── dtos/
│       ├── __init__.py
│       ├── health_metrics.py
│       ├── cashflow_metrics.py
│       ├── team_efficiency_metrics.py
│       ├── alert_item.py
│       └── decision_support_metrics.py
├── application/
│   ├── __init__.py
│   └── services/
│       ├── __init__.py
│       ├── health_service.py
│       ├── cashflow_service.py
│       ├── team_efficiency_service.py
│       ├── alert_service.py
│       └── decision_support_service.py
├── infrastructure/
│   ├── __init__.py
│   └── cache/
│       ├── __init__.py
│       └── redis_cache_service.py
└── interfaces/
    ├── __init__.py
    └── controllers/
        ├── __init__.py
        ├── health_controller.py
        ├── cashflow_controller.py
        ├── team_efficiency_controller.py
        ├── alerts_controller.py
        ├── decision_support_controller.py
        └── legacy_controller.py
```

---

## 5. 数据聚合策略

### 5.1 跨模块数据来源

| 功能模块 | 数据来源 | 聚合方式 |
|----------|----------|----------|
| 经营健康度 | Order, Customer, Payment, FinancePayment | SUM/COUNT + 趋势对比 |
| 现金流 | Payment, FinancePayment, Receivable, Order | SUM/GROUP BY + 账龄分段 |
| 团队效能 | User, Order, Customer, FollowUp | JOIN + GROUP BY team |
| 风险预警 | Order, Receivable, Event, Customer, FollowUp | 规则引擎判断 |
| 决策支撑 | Customer, Order, OrderItem, Supplier, SupplierEvaluation | JOIN + 分组统计 |

### 5.2 权限过滤策略

利用 `require_permission` 中间件返回的 `scope` 进行数据过滤：

```python
async def get_health_metrics(
    period: PeriodType,
    db: AsyncSession,
    scope: str  # all/team/own
) -> HealthMetrics:
    query = select(Order).where(Order.created_at >= period.start)

    if scope == "own":
        # 只看本人的订单
        query = query.where(Order.sale_id == current_user.id)
    elif scope == "team":
        # 看本团队的订单
        query = query.where(Order.sale_user.team == current_user.team)
    # scope == "all" 无过滤

    # ... 执行查询并聚合
```

### 5.3 数据库查询优化

1. **索引利用** — 利用现有表的索引：
   - `orders(sale_id, status, created_at)`
   - `customers(status, assigned_sale_id, source_id)`
   - `payments(paid_at, status, method)`
   - `events(date, status)`

2. **聚合查询优化** — 使用 SQLAlchemy 的聚合函数：
   ```python
   result = await db.execute(
       select(
           User.id,
           User.name,
           func.count(Order.id).label("order_count"),
           func.sum(Order.total_amount).label("total_amount")
       )
       .join(Order, Order.sale_id == User.id)
       .where(Order.created_at >= period.start)
       .group_by(User.id, User.name)
   )
   ```

3. **分页处理** — 排行榜类查询支持分页：
   ```python
   query = query.limit(page_size).offset((page - 1) * page_size)
   ```

---

## 6. 缓存策略

### 6.1 缓存 Key 设计

| 数据类型 | Key 格式 | TTL | 失效策略 |
|----------|----------|-----|----------|
| 经营健康度 | `dashboard:health:{period}:{scope}:{user_id}` | 5min | 数据更新时失效 |
| 现金流数据 | `dashboard:cashflow:{period}:{scope}:{user_id}` | 5min | 数据更新时失效 |
| 团队效能 | `dashboard:team:{period}:{team}:{scope}:{user_id}` | 5min | 数据更新时失效 |
| 风险预警 | `dashboard:alerts:{level}:{scope}:{user_id}` | 1min | 高频刷新 |
| 决策支撑 | `dashboard:decision:{period}:{dimension}:{scope}` | 10min | 低频变化 |

### 6.2 缓存失效

- **主动失效** — 在数据变更时清理相关缓存：
  ```python
  await cache_service.delete_pattern(f"dashboard:health:{period}:*")
  ```

- **被动失效** — 依赖 TTL 自动过期

### 6.3 缓存穿透防护

对于不存在的数据，缓存空值并设置较短 TTL（30s）：

```python
if data is None:
    await redis_client.setex(cache_key, 30, "NULL")
```

---

## 7. 与其他模块的交互

### 7.1 依赖关系

```
┌─────────────────────────────────────────────────────────────────┐
│                        Dashboard Module                         │
├─────────────────────────────────────────────────────────────────┤
│  Depends On (Read-Only):                                        │
│  - Order (订单)         — 读取订单统计、销售排行                 │
│  - Customer (客户)      — 读取客户统计、转化漏斗                 │
│  - User (用户)          — 读取销售团队信息                       │
│  - Event (活动)         — 读取排期信息                           │
│  - Payment (收款)       — 读取收款统计                           │
│  - Finance (财务)       — 读取应收/财务支付数据（可选，如未迁移） │
│  - Supplier (供应商)    — 读取供应商评价数据                     │
│                                                                 │
│  Events (Publish):                                               │
│  - DASHBOARD_VIEWED — 用户查看工作台（埋点统计）                 │
│                                                                 │
│  Used By:                                                       │
│  - Frontend (Vue 3)     — 通过 HTTP API 获取数据                │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 数据访问方式

Dashboard 模块**不引入新的仓储**，而是：

1. **直接查询 Model** — 对于简单的统计查询，直接使用 SQLAlchemy
2. **调用现有 Service** — 对于复杂业务逻辑，调用其他模块暴露的 Service：
   - Finance 模块的 `FinanceStatsService.get_dashboard_summary()`
   - 但避免过度依赖，保持 Dashboard 的独立性

### 7.3 事件发布

| 事件 | 触发条件 | 订阅者 |
|------|----------|--------|
| `DASHBOARD_VIEWED` | 用户查看工作台 | 埋点系统 |

---

## 8. 扩展点

### 8.1 新增统计指标

在对应的 Service 中添加查询方法，更新 DTO 和 Controller。

### 8.2 新增预警规则

在 `AlertService` 中添加新的预警规则方法：

```python
async def check_new_alert_type(self, scope: str, user_id: int) -> list[AlertItem]:
    # 实现新的预警逻辑
    pass
```

### 8.3 缓存策略调整

通过配置文件或环境变量调整 TTL：

```python
DASHBOARD_CACHE_TTL = {
    "health": 300,      # 5分钟
    "cashflow": 300,
    "alerts": 60,       # 1分钟
    "decision": 600,    # 10分钟
}
```

---

## 9. 性能考虑

### 9.1 查询性能

1. **并行请求** — 前端可并行请求各模块 API，后端不强制串行
2. **数据库连接池** — 使用异步连接池，避免阻塞
3. **聚合优化** — 使用数据库聚合函数，减少数据传输量

### 9.2 缓存命中率

1. **缓存预热** — 系统启动时预加载常用数据
2. **缓存监控** — 记录缓存命中率，优化缓存策略

### 9.3 数据量限制

1. **排行榜限制** — 默认返回 Top 20，支持分页
2. **预警列表限制** — 默认返回最近 100 条预警
3. **明细数据导出** — 提供异步导出功能

---

## 10. 安全考虑

### 10.1 数据权限

| 角色 | 经营健康度 | 现金流 | 团队效能 | 风险预警 | 决策支撑 |
|------|-----------|--------|----------|----------|----------|
| 管理员 | all | all | all | all | all |
| 销售总监 | all | read | all | all | all |
| 销售主管 | all | team | team | team | team |
| 销售 | own | none | own | own | none |
| 财务总监 | read | all | read | all | all |
| 策划总监 | read | none | read | team | - |

### 10.2 敏感数据脱敏

- 客户电话号码中间 4 位掩码
- 财务金额仅展示给有权限的用户

### 10.3 审计日志

记录 Dashboard 查看操作（可选，用于分析使用习惯）：
```python
await audit_log.log("dashboard_viewed", user_id, {"period": period})
```

---

## 11. 测试策略

### 11.1 单元测试

- Service 层各方法的聚合逻辑
- PeriodRange 计算准确性
- 趋势对比计算准确性

### 11.2 集成测试

- 完整的 API 请求-响应流程
- 权限过滤正确性
- 缓存读写正确性

### 11.3 性能测试

- 1000+ 订单的统计查询性能
- 并发请求下的响应时间
- 缓存命中率
