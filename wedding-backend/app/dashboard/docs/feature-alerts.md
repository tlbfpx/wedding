# 风险预警功能详细设计

> 功能编号: FH-004
> 所属模块: Dashboard
> 创建日期: 2026-06-04

---

## 1. 功能概述

主动发现经营风险，提前介入处理，避免小问题变成大损失。

---

## 2. 预警规则定义

### 2.1 逾期应收（Overdue Receivable）

**触发条件**:
- 单笔逾期 > 5 万
- 或累计逾期 > 10 万

**数据来源**:
```sql
SELECT r.id, r.order_id, o.order_no, o.customer_name,
       (r.total_amount - r.received_amount) as overdue_amount,
       CURRENT_DATE - r.due_date as overdue_days,
       o.sale_id as owner_id, u.name as owner_name
FROM receivables r
JOIN orders o ON o.id = r.order_id
JOIN users u ON u.id = o.sale_id
WHERE r.status != 'paid'
  AND r.due_date < CURRENT_DATE
```

**级别**: 高（high）

**操作**: `view_detail`, `mark_resolved`

---

### 2.2 即将到期活动（Upcoming Event）

**触发条件**:
- 3 天内未确认的活动

**数据来源**:
```sql
SELECT e.id, e.title, e.date, e.planner_id as owner_id, u.name as owner_name
FROM events e
JOIN users u ON u.id = e.planner_id
WHERE e.date BETWEEN CURRENT_DATE AND CURRENT_DATE + 3
  AND e.status NOT IN ('confirmed', 'cancelled')
```

**级别**: 中（medium）

**操作**: `view_detail`, `send_remind`

---

### 2.3 长期未跟进（Long No Follow-up）

**触发条件**:
- 意向客户 > 7 天未跟进

**数据来源**:
```sql
SELECT c.id, c.name, c.assigned_sale_id as owner_id, u.name as owner_name,
       MAX(fu.created_at) as last_follow_at,
       CURRENT_DATE - MAX(fu.created_at) as days_since_follow
FROM customers c
JOIN users u ON u.id = c.assigned_sale_id
LEFT JOIN follow_ups fu ON fu.customer_id = c.id
WHERE c.status = 'intention'
  AND c.assigned_sale_id IS NOT NULL
GROUP BY c.id, c.name, c.assigned_sale_id, u.name
HAVING CURRENT_DATE - MAX(fu.created_at) > 7
   OR MAX(fu.created_at) IS NULL
```

**级别**: 中（medium）

**操作**: `view_detail`, `assign_follow`

---

### 2.4 高风险客户（High Risk Customer）

**触发条件**:
- 预算低于平均客单价 30%
- 且为首次咨询（无历史订单）

**数据来源**:
```python
avg_order_value = await get_avg_order_value()
high_risk_customers = []
for customer in intention_customers:
    budget_lower = parse_budget_range(customer.budget_range)[0]
    if budget_lower < avg_order_value * 0.7:
        high_risk_customers.append(customer)
```

**级别**: 中（medium）

**操作**: `view_detail`

---

### 2.5 供应商风险（Supplier Risk）

**触发条件**:
- 供应商评分 < 3.5
- 且本月有排期

**数据来源**:
```sql
SELECT s.id, s.name, s.rating, COUNT(e.id) as upcoming_count
FROM suppliers s
JOIN events e ON e.venue_id = s.id  OR s.id IN (...)
WHERE s.rating < 3.5
  AND e.date BETWEEN :month_start AND :month_end
GROUP BY s.id, s.name, s.rating
```

**级别**: 中（medium）

**操作**: `view_detail`

---

### 2.6 目标告急（Target Alert）

**触发条件**:
- 营收达成率 < 60%
- 且本月只剩 10 天

**数据来源**:
```python
today = date.today()
days_remaining = (month_end - today).days
current_revenue = await get_current_month_revenue()
target = await get_revenue_target(month)
achievement = current_revenue / target.amount if target else 0

if achievement < 0.6 and days_remaining <= 10:
    # 触发预警
```

**级别**: 高（high）

**操作**: `view_detail`, `adjust_target`

---

## 3. API 契约

详见 `contracts.md` §1.4

---

## 4. Service 实现

### 4.1 AlertService

```python
class AlertService:
    """风险预警服务"""

    async def get_alerts(
        self,
        level: Optional[AlertLevel],
        type_filter: Optional[str],
        limit: int,
        offset: int,
        scope: str,
        user_id: int,
        db: AsyncSession
    ) -> tuple[int, list[AlertItem]]:
        """获取预警列表"""
        alerts = []

        # 根据规则检查各类预警
        if level in (None, AlertLevel.high, AlertLevel.medium):
            alerts.extend(await self._check_overdue_receivables(scope, user_id, db))
            alerts.extend(await self._check_upcoming_events(scope, user_id, db))
            alerts.extend(await self._check_long_no_follow(scope, user_id, db))
            alerts.extend(await self._check_target_alert(scope, user_id, db))

        # 级别过滤
        if level:
            alerts = [a for a in alerts if a.level == level]

        # 类型过滤
        if type_filter:
            alerts = [a for a in alerts if a.type == type_filter]

        # 分页
        total = len(alerts)
        alerts = alerts[offset:offset + limit]

        return total, alerts

    async def mark_resolved(
        self,
        alert_id: str,
        note: str,
        user_id: int,
        db: AsyncSession
    ) -> bool:
        """标记预警已处理"""
        # 记录处理日志
        # 清除缓存
        return True
```

---

## 5. 缓存策略

- **Key**: `dashboard:alerts:{level}:{type}:{scope}:{user_id}`
- **TTL**: 60 秒（高频刷新）

---

## 6. 权限控制

- `dashboard:read`
- 根据 `scope` 过滤：只显示用户权限范围内的预警

---

## 7. 前端交互

### 7.1 布局

```
┌─────────────────────────────────────────────────────────────┐
│  风险预警                                      [自动刷新:5分钟] │
├─────────────────────────────────────────────────────────────┤
│  🔴 高风险 (3)                                  🟡 中风险 (7) │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 🔴 逾期应收：客户张三的婚礼订单(¥58,000)已逾期15天          ││
│  │    负责人：李四 | 操作：[查看详情] [标记已处理]             ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │ 🔴 目标告急：本月营收达成率仅58%，距月底仅剩10天            ││
│  │    操作：[查看营收明细] [调整目标]                           ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │ 🟡 即将到期：客户李七的婚礼(3天后)尚未确认最终方案          ││
│  │    负责人：周八 | 操作：[查看活动] [发送提醒]                ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │ 🟡 长期未跟进：客户陈九(意向状态)已12天未跟进               ││
│  │    负责人：吴十 | 操作：[查看客户] [分配跟进]               ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 7.2 交互规则

- 预警卡片按级别分组，高风险优先展示
- 自动刷新（可配置间隔）
- 支持标记已处理
- 支持快速操作（发送提醒、分配跟进）

---

## 8. 验收标准

- [ ] 逾期应收识别准确
- [ ] 即将到期活动识别准确
- [ ] 长期未跟进客户识别准确
- [ ] 目标告急判断准确
- [ ] 预警级别正确
- [ ] 预警操作可用
- [ ] 权限过滤正确
- [ ] 缓存生效，自动刷新
