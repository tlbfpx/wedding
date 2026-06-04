# Dashboard 模块重构变更日志

**日期**: 2026-06-04
**功能**: FR-018 Dashboard 管理层驾驶舱重构
**影响模块**: app/dashboard

---

## 变更背景

原有 Dashboard 模块存在以下问题：
1. 单文件路由 (api/dashboard.py) 包含所有查询逻辑，可维护性差
2. 缺少领域模型，查询逻辑分散
3. 无统一缓存策略
4. 权限过滤简陋，依赖前端传参
5. 缺少数据聚合层

## 变更方案

### 1. 架构重构

将 Dashboard 从单文件路由重构为 DDD 分层模块：

```
app/dashboard/
├── domain/
│   ├── value_objects/      # PeriodRange, MetricValue, AlertLevel, enums
│   └── dtos/               # HealthMetrics, CashflowMetrics, etc.
├── application/
│   └── services/           # 5 个业务服务
├── infrastructure/
│   └── cache/              # RedisCacheService
└── interfaces/
    └── controllers/        # 6 个 Controller
```

### 2. 新增 API

| API | 功能 | 权限 | 缓存TTL |
|-----|------|------|---------|
| GET /api/v1/dashboard/health | 经营健康度 | dashboard:read | 300s |
| GET /api/v1/dashboard/cashflow | 现金流与应收 | dashboard:read + finance:read | 300s |
| GET /api/v1/dashboard/team-efficiency | 团队效能 | dashboard:read | 300s |
| GET /api/v1/dashboard/alerts | 风险预警 | dashboard:read | 60s |
| POST /api/v1/dashboard/alerts/{id}/resolve | 标记预警已处理 | dashboard:write | - |
| GET /api/v1/dashboard/decision-support | 决策支撑 | dashboard:read_all | 600s |

### 3. 核心功能实现

#### 经营健康度
- 营收、订单数、客单价、签约率、毛利
- 支持环比/同比对比
- 目标达成率分析

#### 现金流与应收
- 现金流入按付款方式分布
- 应收余额、逾期应收、账龄分析
- 应收周转天数

#### 团队效能
- 团队对比（营收、人数、人均产出）
- 转化漏斗（潜在→跟进→意向→签约→流失）
- 销售排行（支持分页）

#### 风险预警
- 逾期应收预警（>5万）
- 即将到期活动提醒（3天内）
- 长期未跟进客户（>7天）
- 预警级别分级

#### 决策支撑
- 客户来源 ROI 分析
- 服务类型收入占比
- 供应商性价比评分

### 4. 缓存策略

| 数据类型 | Key 格式 | TTL | 失效策略 |
|----------|----------|-----|----------|
| 经营健康度 | dashboard:health:{period}:{compare}:{scope}:{user_id} | 300s | 数据更新时失效 |
| 现金流数据 | dashboard:cashflow:{period}:{scope}:{user_id} | 300s | 数据更新时失效 |
| 团队效能 | dashboard:team:{period}:{team}:{page}:{scope}:{user_id} | 300s | 数据更新时失效 |
| 风险预警 | dashboard:alerts:{level}:{type}:{scope}:{user_id} | 60s | 高频刷新 |
| 决策支撑 | dashboard:decision:{period}:{dimension}:{scope} | 600s | 低频变化 |

### 5. 权限控制

所有 API 通过 require_permission 中间件验证，并根据返回的 scope 过滤数据：
- scope == "all" → 无过滤，返回全局数据
- scope == "team" → 过滤为本团队数据
- scope == "own" → 过滤为本人数据

### 6. DTO 序列化

使用 Pydantic BaseModel 替代 dataclass，确保 FastAPI 正确序列化响应：
- HealthMetrics
- MetricValueResponse
- 所有其他 DTO

## 向后兼容性

### 保留的旧 API
以下 API 保持可用，添加 deprecated=True 标记：
- GET /api/v1/dashboard/overview
- GET /api/v1/dashboard/sales-ranking
- GET /api/v1/dashboard/conversion-funnel
- GET /api/v1/dashboard/finance-summary

### 废弃的 API
- GET /api/v1/dashboard/schedule-heatmap → 保留
- GET /api/v1/dashboard/supplier-ranking → 保留

## 测试覆盖

- 单元测试：tests/test_dashboard_health.py
- 覆盖场景：
  - 不同周期（月/季/年）
  - 对比周期（环比/同比）
  - 缓存生效
  - 权限验证
  - 参数校验

## 性能优化

1. 数据库查询优化：使用 SQLAlchemy 聚合函数
2. 缓存策略：高频数据缓存，低频数据实时计算
3. 分页支持：排行榜类查询支持分页

## 后续改进方向

1. 添加更多单元测试和集成测试
2. 实现缓存预热机制
3. 添加 Prometheus 指标监控
4. 实现预警规则的数据库配置化
5. 添加异步导出功能

---

**相关文档**:
- 设计概览: docs/design-overview.md
- 接口契约: docs/contracts.md
- 功能详设: docs/feature-*.md
