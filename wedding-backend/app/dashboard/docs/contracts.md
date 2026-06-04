# Dashboard 模块 - 接口契约

> 模块路径: `app/dashboard`
> API 前缀: `/api/v1/dashboard`
> 版本: v2.0
> 创建日期: 2026-06-04

---

## 1. Controller 接口（HTTP API）

### 1.1 经营健康度 API

#### GET /api/v1/dashboard/health

获取经营健康度核心指标。

**Query Parameters:**
```python
{
    "period": Literal["month", "quarter", "year"] = "month",
    "compare_to": Literal["prev_period", "same_period_last_year"] = "prev_period"
}
```

**Response:**
```python
{
    "period": "month",
    "period_start": "2026-06-01",
    "period_end": "2026-06-30",
    "compare_period_start": "2026-05-01",  # 可选
    "compare_period_end": "2026-05-31",    # 可选
    "metrics": {
        "revenue": {
            "value": 1285000.00,
            "trend": 0.125,          # 可选，环比增长率
            "target": 1500000.00,    # 可选，目标值
            "achievement": 0.85      # 可选，达成率
        },
        "orders": {
            "value": 42,
            "trend": 0.083
        },
        "avg_order_value": {
            "value": 30600.00,
            "trend": -0.032
        },
        "sign_rate": {
            "value": 0.68,
            "trend": 0.051
        },
        "gross_profit": {
            "value": 452000.00,
            "trend": 0.158,
            "target": 490000.00,
            "achievement": 0.92
        }
    }
}
```

**权限:** `dashboard:read`（根据 scope 返回对应范围的数据）

**缓存:** TTL 300s

---

### 1.2 现金流与应收 API

#### GET /api/v1/dashboard/cashflow

获取现金流与应收分析数据。

**Query Parameters:**
```python
{
    "period": Literal["month", "quarter", "year"] = "month"
}
```

**Response:**
```python
{
    "period": "month",
    "period_start": "2026-06-01",
    "period_end": "2026-06-30",
    "cash_in": {
        "total": 982000.00,
        "by_method": {
            "wechat": 441900.00,
            "bank": 343700.00,
            "cash": 147300.00,
            "alipay": 49100.00
        }
    },
    "receivables": {
        "total": 325000.00,
        "overdue": 58000.00,
        "overdue_count": 3
    },
    "aging": [
        {"bucket": "0-30", "amount": 195000.00, "percent": 60},
        {"bucket": "31-60", "amount": 81250.00, "percent": 25},
        {"bucket": "61-90", "amount": 32500.00, "percent": 10},
        {"bucket": "90+", "amount": 16250.00, "percent": 5}
    ],
    "turnover_days": 38,
    "payments": {
        "total": 450000.00,
        "paid": 380000.00,
        "pending": 70000.00
    }
}
```

**权限:** `dashboard:read` + `finance:read`（根据 scope 过滤）

**缓存:** TTL 300s

---

### 1.3 团队效能 API

#### GET /api/v1/dashboard/team-efficiency

获取团队效能数据。

**Query Parameters:**
```python
{
    "period": Literal["month", "quarter", "year"] = "month",
    "team": Optional[str] = None,  # 团队筛选
    "page": int = 1,
    "page_size": int = 20
}
```

**Response:**
```python
{
    "period": "month",
    "period_start": "2026-06-01",
    "period_end": "2026-06-30",
    "teams": [
        {
            "team": "sales",
            "total_revenue": 452000.00,
            "headcount": 5,
            "avg_revenue": 90400.00
        }
    ],
    "funnel": [
        {"stage": "potential", "count": 120, "rate": 1.0},
        {"stage": "following", "count": 78, "rate": 0.65},
        {"stage": "intention", "count": 50, "rate": 0.42},
        {"stage": "signed", "count": 32, "rate": 0.27},
        {"stage": "lost", "count": 6, "rate": 0.05}
    ],
    "new_customers": 45,
    "follow_up_count": 235,
    "ranking": [
        {
            "rank": 1,
            "sale_id": 1,
            "sale_name": "张三",
            "team": "sales",
            "order_count": 12,
            "revenue": 368000.00,
            "avg_order_value": 30667.00,
            "conversion_rate": 0.75,
            "follow_up_count": 48
        }
    ],
    "total": 42,
    "page": 1,
    "page_size": 20
}
```

**权限:** `dashboard:read`（根据 scope 过滤，own/team/all）

**缓存:** TTL 300s

---

### 1.4 风险预警 API

#### GET /api/v1/dashboard/alerts

获取风险预警列表。

**Query Parameters:**
```python
{
    "level": Literal["all", "high", "medium", "low"] = "all",
    "type": Optional[str] = None,  # overdue_receivable/upcoming_event/long_no_follow/etc.
    "limit": int = 20,
    "offset": int = 0
}
```

**Response:**
```python
{
    "high_count": 3,
    "medium_count": 7,
    "low_count": 0,
    "alerts": [
        {
            "id": "alert_overdue_123",
            "level": "high",
            "type": "overdue_receivable",
            "title": "逾期应收：客户张三的婚礼订单",
            "detail": "订单 WD202605001-001，逾期15天，金额 ¥58,000",
            "entity_type": "order",
            "entity_id": 123,
            "owner_id": 5,
            "owner_name": "李四",
            "actions": ["view_detail", "mark_resolved"],
            "created_at": "2026-06-01T10:30:00Z"
        },
        {
            "id": "alert_event_456",
            "level": "medium",
            "type": "upcoming_event",
            "title": "即将到期：客户李七的婚礼",
            "detail": "3天后尚未确认最终方案",
            "entity_type": "event",
            "entity_id": 456,
            "owner_id": 8,
            "owner_name": "周八",
            "actions": ["view_detail", "send_remind"],
            "created_at": "2026-06-03T09:00:00Z"
        }
    ],
    "total": 10
}
```

**权限:** `dashboard:read`（根据 scope 过滤）

**缓存:** TTL 60s

#### POST /api/v1/dashboard/alerts/{alert_id}/resolve

标记预警已处理。

**Path Parameters:**
```python
{
    "alert_id": str
}
```

**Request Body:**
```python
{
    "note": str = ""  # 可选，处理说明
}
```

**Response:**
```python
{
    "success": true,
    "resolved_at": "2026-06-04T10:30:00Z"
}
```

**权限:** `dashboard:write`

**缓存:** 操作后清除对应预警缓存

---

### 1.5 决策支撑 API

#### GET /api/v1/dashboard/decision-support

获取决策支撑数据。

**Query Parameters:**
```python
{
    "period": Literal["month", "quarter", "year"] = "month",
    "dimension": Literal["source", "service", "supplier"] = "source"
}
```

**Response:**
```python
{
    "period": "month",
    "period_start": "2026-06-01",
    "period_end": "2026-06-30",
    "source_roi": [
        {
            "source": "小红书",
            "source_id": 1,
            "lead_count": 45,
            "signed_count": 32,
            "conversion_rate": 0.71,
            "revenue": 980000.00,
            "avg_order_value": 30625.00,
            "roi_score": 5  # 1-5 星级
        },
        {
            "source": "朋友介绍",
            "source_id": 2,
            "lead_count": 38,
            "signed_count": 30,
            "conversion_rate": 0.79,
            "revenue": 920000.00,
            "avg_order_value": 30667.00,
            "roi_score": 5
        }
    ],
    "service_breakdown": [
        {
            "service_type": "planning",
            "revenue": 578000.00,
            "percent": 0.45,
            "count": 25
        },
        {
            "service_type": "photo",
            "revenue": 321000.00,
            "percent": 0.25,
            "count": 18
        }
    ],
    "supplier_value": [
        {
            "supplier_id": 1,
            "supplier_name": "某某花艺",
            "type": "floral",
            "cooperation_count": 12,
            "total_amount": 156000.00,
            "avg_rating": 4.8,
            "value_score": 5
        }
    ]
}
```

**权限:** `dashboard:read_all`（仅管理层可见）

**缓存:** TTL 600s

---

## 2. Service 接口（暴露给其他模块）

### 2.1 DashboardStatsService

```python
class DashboardStatsService:
    """Dashboard 统计服务（供其他模块调用）"""

    async def get_health_summary(
        self,
        period: PeriodType = PeriodType.MONTH,
        scope: str = "all",
        user_id: Optional[int] = None
    ) -> dict:
        """获取经营健康度摘要

        Args:
            period: 统计周期
            scope: 数据范围 (all/team/own)
            user_id: 当前用户ID（scope过滤用）

        Returns:
            dict: {
                "revenue": float,
                "orders": int,
                "avg_order_value": float,
                "sign_rate": float,
                "gross_profit": float
            }
        """

    async def get_cashflow_summary(
        self,
        period: PeriodType = PeriodType.MONTH,
        scope: str = "all",
        user_id: Optional[int] = None
    ) -> dict:
        """获取现金流摘要

        Returns:
            dict: {
                "cash_in": float,
                "receivable_total": float,
                "overdue_amount": float
            }
        """

    async def check_alerts(
        self,
        level: Optional[AlertLevel] = None,
        scope: str = "all",
        user_id: Optional[int] = None
    ) -> list[AlertItem]:
        """检查预警

        Returns:
            list[AlertItem]: 预警列表
        """
```

---

## 3. Events（领域事件）

### 3.1 本模块发布的事件

| 事件名称 | 触发条件 | 负载（Payload） |
|----------|----------|----------------|
| `DASHBOARD_VIEWED` | 用户查看工作台 | `{user_id, period, timestamp}` |
| `ALERT_RESOLVED` | 预警标记已处理 | `{alert_id, user_id, note, timestamp}` |

### 3.2 本模块订阅的事件

| 事件名称 | 来源模块 | 处理动作 |
|----------|----------|----------|
| （暂无订阅） | - | - |

---

## 4. 权限定义

### 4.1 权限标识

| 权限 | 说明 |
|------|------|
| `dashboard:read` | 查看工作台基础数据（根据 scope 过滤） |
| `dashboard:read_all` | 查看全局数据（管理层驾驶舱） |
| `dashboard:read_team` | 查看团队数据（主管级） |
| `dashboard:write` | 工作台写操作（标记预警已处理等） |

### 4.2 权限矩阵

| 角色 | read | read_all | read_team | write |
|------|------|----------|-----------|-------|
| 管理员 | all | all | all | all |
| 销售总监 | all | all | all | all |
| 销售主管 | team | - | team | own |
| 销售 | own | - | - | own |
| 财务总监 | read | read | - | - |
| 策划总监 | read | - | team | - |

### 4.3 Scope 过滤规则

```python
# require_permission 返回的 scope 决定数据过滤范围
scope == "all"   → 无过滤，返回全局数据
scope == "team"  → 过滤为本团队数据
scope == "own"   → 过滤为本人数据
```

---

## 5. 错误码定义

| 错误码 | HTTP状态 | 说明 |
|--------|----------|------|
| `INVALID_PERIOD` | 400 | 无效的时间周期参数 |
| `INVALID_COMPARE_TO` | 400 | 无效的对比周期参数 |
| `INVALID_DIMENSION` | 400 | 无效的决策支撑维度 |
| `ALERT_NOT_FOUND` | 404 | 预警不存在或已处理 |
| `INSUFFICIENT_PERMISSION` | 403 | 权限不足（如非管理层访问决策支撑） |

---

## 6. API 变更说明

### 6.1 新增 API

| API | 用途 |
|-----|------|
| `GET /api/v1/dashboard/health` | 经营健康度数据 |
| `GET /api/v1/dashboard/cashflow` | 现金流与应收数据 |
| `GET /api/v1/dashboard/team-efficiency` | 团队效能数据 |
| `GET /api/v1/dashboard/alerts` | 风险预警列表 |
| `POST /api/v1/dashboard/alerts/:id/resolve` | 标记预警已处理 |
| `GET /api/v1/dashboard/decision-support` | 决策支撑数据 |

### 6.2 保留的旧 API（向后兼容）

| API | 说明 |
|-----|------|
| `GET /api/dashboard/schedule-heatmap` | 排期热力图 |
| `GET /api/dashboard/supplier-ranking` | 供应商排行 |

### 6.3 废弃的 API

| API | 替换为 |
|-----|--------|
| `GET /api/dashboard/overview` | `/api/v1/dashboard/health` |
| `GET /api/dashboard/sales-ranking` | `/api/v1/dashboard/team-efficiency` |
| `GET /api/dashboard/conversion-funnel` | `/api/v1/dashboard/team-efficiency` |
| `GET /api/dashboard/finance-summary` | `/api/v1/dashboard/cashflow` |

废弃 API 响应头添加 `Deprecation: true`，建议 6 个月后移除。

---

## 7. Request/Response Schema

### 7.1 PeriodType

```python
class PeriodType(str, enum.Enum):
    month = "month"
    quarter = "quarter"
    year = "year"
```

### 7.2 AlertLevel

```python
class AlertLevel(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"
```

### 7.3 MetricValue Response

```python
class MetricValueResponse(BaseModel):
    value: Decimal
    trend: Optional[float] = None
    target: Optional[Decimal] = None
    achievement: Optional[float] = None
```

### 7.4 AlertItem Response

```python
class AlertItemResponse(BaseModel):
    id: str
    level: AlertLevel
    type: str
    title: str
    detail: str
    entity_type: str
    entity_id: int
    owner_id: Optional[int]
    owner_name: Optional[str]
    actions: list[str]
    created_at: datetime
```

---

## 8. 示例请求

### 8.1 获取本月经营健康度

```bash
GET /api/v1/dashboard/health?period=month&compare_to=prev_period
Authorization: Bearer <token>
```

**Response:**
```json
{
    "period": "month",
    "period_start": "2026-06-01",
    "period_end": "2026-06-30",
    "metrics": {
        "revenue": {"value": 1285000.00, "trend": 0.125},
        "orders": {"value": 42, "trend": 0.083}
    }
}
```

### 8.2 获取高风险预警

```bash
GET /api/v1/dashboard/alerts?level=high&limit=10
Authorization: Bearer <token>
```

### 8.3 标记预警已处理

```bash
POST /api/v1/dashboard/alerts/alert_overdue_123/resolve
Authorization: Bearer <token>
Content-Type: application/json

{
    "note": "已联系客户，承诺本周付款"
}
```
