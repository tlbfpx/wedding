# 决策支撑功能详细设计

> 功能编号: FH-005
> 所属模块: Dashboard
> 创建日期: 2026-06-04

---

## 1. 功能概述

为管理层提供资源分配决策依据：哪个获客渠道最有效、哪些服务最赚钱、哪些供应商性价比最高。

---

## 2. 分析维度定义

### 2.1 客户来源 ROI（Source ROI）

**定义**: 各渠道获客成本 vs 产出分析

**计算逻辑**:
```sql
SELECT
    cs.id as source_id,
    cs.name as source,
    COUNT(c.id) as lead_count,
    COUNT(CASE WHEN c.status = 'signed' THEN 1 END) as signed_count,
    COALESCE(SUM(o.total_amount), 0) as revenue
FROM customer_sources cs
LEFT JOIN customers c ON c.source_id = cs.id
    AND c.created_at >= :period_start
    AND c.created_at < :period_end
LEFT JOIN orders o ON o.customer_id = c.id
    AND o.created_at >= :period_start
    AND o.created_at < :period_end
    AND o.status IN ('signed', 'executing', 'completed')
GROUP BY cs.id, cs.name
```

**衍生指标**:
- `conversion_rate` = signed_count / lead_count
- `avg_order_value` = revenue / signed_count
- `roi_score` = 综合评分（1-5 星）

**ROI 评分规则**:
```python
def calculate_roi_score(lead_count, conversion_rate, avg_order_value):
    score = 1
    # 转化率权重 40%
    if conversion_rate >= 0.7: score += 2
    elif conversion_rate >= 0.5: score += 1

    # 获客数权重 30%
    if lead_count >= 40: score += 2
    elif lead_count >= 20: score += 1

    # 客单价权重 30%
    if avg_order_value >= 30000: score += 1
    elif avg_order_value >= 25000: score += 0.5

    return min(5, int(score) + 1)
```

---

### 2.2 服务类型收入占比（Service Breakdown）

**定义**: 各服务类型的收入分布

**计算逻辑**:
```sql
SELECT
    oi.type as service_type,
    SUM(oi.amount) as revenue,
    COUNT(DISTINCT oi.order_id) as count
FROM order_items oi
JOIN orders o ON o.id = oi.order_id
WHERE o.created_at >= :period_start
  AND o.created_at < :period_end
  AND o.status IN ('signed', 'executing', 'completed')
GROUP BY oi.type
ORDER BY revenue DESC
```

**百分比计算**:
```python
total_revenue = sum(item.revenue for item in items)
for item in items:
    item.percent = item.revenue / total_revenue
```

---

### 2.3 供应商性价比（Supplier Value）

**定义**: 供应商价格 vs 评分 vs 合作频次

**计算逻辑**:
```sql
SELECT
    s.id as supplier_id,
    s.name as supplier_name,
    s.type,
    COUNT(DISTINCT oi.order_id) as cooperation_count,
    SUM(oi.amount) as total_amount,
    AVG(se.rating) as avg_rating
FROM suppliers s
JOIN order_items oi ON oi.supplier_id = s.id
JOIN orders o ON o.id = oi.order_id
    AND o.created_at >= :period_start
    AND o.created_at < :period_end
LEFT JOIN supplier_evaluations se ON se.supplier_id = s.id
GROUP BY s.id, s.name, s.type
```

**性价比评分规则**:
```python
def calculate_value_score(cooperation_count, avg_rating, total_amount):
    score = 1
    # 评分权重 50%
    if avg_rating >= 4.5: score += 2.5
    elif avg_rating >= 4.0: score += 2
    elif avg_rating >= 3.5: score += 1

    # 合作频次权重 30%
    if cooperation_count >= 10: score += 1.5
    elif cooperation_count >= 5: score += 1

    # 交易金额权重 20%
    if total_amount >= 100000: score += 1
    elif total_amount >= 50000: score += 0.5

    return min(5, int(score) + 1)
```

---

## 3. API 契约

详见 `contracts.md` §1.5

---

## 4. Service 实现

### 4.1 DecisionSupportService

```python
class DecisionSupportService:
    """决策支撑服务"""

    async def get_metrics(
        self,
        period: PeriodType,
        dimension: DecisionDimension,
        scope: str,
        user_id: int,
        db: AsyncSession
    ) -> DecisionSupportMetrics:
        """获取决策支撑数据"""
        period_range = PeriodRange.from_period(period)

        # 根据维度获取数据
        if dimension in (DecisionDimension.source, DecisionDimension.all):
            source_roi = await self._get_source_roi(period_range, scope, user_id, db)
        else:
            source_roi = []

        if dimension in (DecisionDimension.service, DecisionDimension.all):
            service_breakdown = await self._get_service_breakdown(period_range, scope, user_id, db)
        else:
            service_breakdown = []

        if dimension in (DecisionDimension.supplier, DecisionDimension.all):
            supplier_value = await self._get_supplier_value(period_range, scope, user_id, db)
        else:
            supplier_value = []

        return DecisionSupportMetrics(
            period=period,
            source_roi=source_roi,
            service_breakdown=service_breakdown,
            supplier_value=supplier_value
        )
```

---

## 5. 缓存策略

- **Key**: `dashboard:decision:{period}:{dimension}:{scope}`
- **TTL**: 600 秒（低频变化）

---

## 6. 权限控制

- `dashboard:read_all`（仅管理层可见）
- 数据不过滤，始终返回全局数据

---

## 7. 前端交互

### 7.1 布局

```
┌─────────────────────────────────────────────────────────────┐
│  决策支撑                                              [本月▼] │
├─────────────────────────────────────────────────────────────┤
│                                                                     │
│  客户来源 ROI 分析                                转置查看▼          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 来源      获客数 签约数 转化率 总营收   客单价  ROI         ││
│  │ 小红书    45    32    71%   ¥98万   ¥3.06万 ⭐⭐⭐⭐⭐       ││
│  │ 朋友介绍  38    30    79%   ¥92万   ¥3.07万 ⭐⭐⭐⭐⭐       ││
│  │ 抖音      52    25    48%   ¥75万   ¥3.00万 ⭐⭐⭐          ││
│  │ 线下活动  28    18    64%   ¥55万   ¥3.06万 ⭐⭐⭐⭐         ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                     │
│  服务类型收入占比                                                    │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ ████ 策划执行 45%  ¥57.8万                                  ││
│  │ ███ 摄影摄像 25%  ¥32.1万                                   ││
│  │ ██ 主持服务 15%  ¥19.3万                                    ││
│  │ ██ 花艺布置 10%  ¥12.8万                                    ││
│  │ █ 其他服务 5%   ¥6.4万                                      ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 7.2 交互规则

- 支持三种维度切换（客户来源/服务类型/供应商性价比）
- 客户来源支持"转置查看"切换为可视化图表
- 服务类型支持点击下钻
- Tab 切换时懒加载数据

---

## 8. 验收标准

- [ ] 客户来源统计准确
- [ ] 转化率计算正确
- [ ] ROI 评分合理
- [ ] 服务类型收入占比正确
- [ ] 供应商性价比评分合理
- [ ] 支持维度切换
- [ ] 权限控制正确（仅管理层可见）
