# 经营健康度功能详细设计

> 功能编号: FH-001
> 所属模块: Dashboard
> 创建日期: 2026-06-04

---

## 1. 功能概述

管理层打开工作台的第一眼，立即了解公司整体经营状况和健康程度。提供营收、订单数、客单价、签约率、毛利五大核心指标，支持趋势对比和目标达成分析。

---

## 2. 指标定义

### 2.1 营收（Revenue）

**定义**: 本期签约订单的总金额

**计算逻辑**:
```sql
SELECT SUM(total_amount)
FROM orders
WHERE created_at >= :period_start
  AND created_at < :period_end
  AND status IN ('signed', 'executing', 'completed')
```

**趋势计算**:
```python
current_revenue = sum(本期订单总额)
compare_revenue = sum(对比期订单总额)
trend = (current_revenue - compare_revenue) / compare_revenue if compare_revenue > 0 else 0
```

**目标达成**:
```python
target = RevenueTarget.query.filter_by(period=current_period).first()
achievement = current_revenue / target.amount if target else None
```

### 2.2 订单数（Orders）

**定义**: 本期签约订单数量

**计算逻辑**:
```sql
SELECT COUNT(*)
FROM orders
WHERE created_at >= :period_start
  AND created_at < :period_end
  AND status IN ('signed', 'executing', 'completed')
```

### 2.3 客单价（Average Order Value）

**定义**: 本期平均每单金额

**计算逻辑**:
```python
avg_order_value = revenue / orders if orders > 0 else 0
```

### 2.4 签约率（Sign Rate）

**定义**: 意向客户转化为签约客户的比率

**计算逻辑**:
```sql
SELECT
  COUNT(CASE WHEN status = 'signed' THEN 1 END) * 1.0 / COUNT(*) as sign_rate
FROM customers
WHERE created_at >= :period_start
  AND created_at < :period_end
  AND status IN ('signed', 'lost', 'intention')
```

### 2.5 毛利（Gross Profit）

**定义**: 营收减去已付供应商款项

**计算逻辑**:
```python
gross_profit = revenue - total_supplier_payments
```

**注意**: 毛利计算需要统计本期订单相关的供应商付款金额。

---

## 3. API 契约

详见 `contracts.md` §1.1

---

## 4. Service 实现

### 4.1 HealthService

```python
class HealthService:
    """经营健康度服务"""

    async def get_metrics(
        self,
        period: PeriodType,
        compare_to: CompareToType,
        scope: str,
        user_id: int,
        db: AsyncSession
    ) -> HealthMetrics:
        """获取经营健康度指标"""
        # 1. 计算时间范围
        period_range = PeriodRange.from_period(period, compare_to)

        # 2. 并行查询各类指标
        revenue = await self._get_revenue(period_range, scope, user_id, db)
        orders = await self._get_orders_count(period_range, scope, user_id, db)
        sign_rate = await self._get_sign_rate(period_range, scope, user_id, db)
        gross_profit = await self._get_gross_profit(period_range, scope, user_id, db)

        # 3. 计算客单价和趋势
        avg_order_value = revenue.value / orders.value if orders.value > 0 else 0

        # 4. 组装响应
        return HealthMetrics(
            period=period,
            period_start=period_range.start.date(),
            period_end=period_range.end.date(),
            metrics={
                "revenue": revenue,
                "orders": orders,
                "avg_order_value": MetricValue(value=avg_order_value),
                "sign_rate": sign_rate,
                "gross_profit": gross_profit
            }
        )
```

---

## 5. 缓存策略

- **Key**: `dashboard:health:{period}:{compare_to}:{scope}:{user_id}`
- **TTL**: 300 秒
- **失效**: 数据变更时主动失效

---

## 6. 权限控制

- `dashboard:read` 基础权限
- 根据 `scope` 过滤数据：
  - `scope == "own"`: 只看本人的订单
  - `scope == "team"`: 看本团队的订单
  - `scope == "all"`: 看全局数据

---

## 7. 前端交互

### 7.1 卡片展示

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  营收    │  │  订单    │  │  客单价  │  │  签约率  │  │  毛利    │
│ ¥128.5万 │  │   42单   │  │ ¥3.06万  │  │  68%    │  │ ¥45.2万  │
│ ▲ 12.5%  │  │ ▲ 8.3%   │  │ ▼ 3.2%   │  │ ▲ 5.1%   │  │ ▲ 15.8%  │
│ 85%达成  │  │          │  │          │  │          │  │  92%达成  │
└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

### 7.2 交互规则

- 支持月/季/年切换
- 环比/同比可选
- 趋势箭头颜色：绿色增长、红色下降
- 目标达成：<80% 黄色预警，<60% 红色告警
- 点击卡片下钻到明细页面

---

## 8. 验收标准

- [ ] 营收计算准确，包含签约/执行/完成状态的订单
- [ ] 订单数统计准确
- [ ] 客单价 = 营收 / 订单数
- [ ] 签约率 = 签约客户 / (签约+意向+流失)
- [ ] 毛利 = 营收 - 供应商付款
- [ ] 趋势对比计算正确
- [ ] 目标达成率计算正确
- [ ] 缓存生效，响应时间 < 500ms
- [ ] 权限过滤正确
