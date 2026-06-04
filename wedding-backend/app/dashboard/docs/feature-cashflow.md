# 现金流与应收功能详细设计

> 功能编号: FH-002
> 所属模块: Dashboard
> 创建日期: 2026-06-04

---

## 1. 功能概述

管理层最关心的财务健康：钱进来多少、还没回来多少、是否逾期、资金周转如何。

---

## 2. 指标定义

### 2.1 现金流入（Cash In）

**定义**: 本期实际收到的款项总额，按付款方式分布

**计算逻辑**:
```sql
SELECT method, SUM(amount)
FROM payments
WHERE paid_at >= :period_start
  AND paid_at < :period_end
  AND status = 'confirmed'
GROUP BY method
```

### 2.2 应收余额（Receivable Total）

**定义**: 尚未收回的款项总额

**计算逻辑**:
```sql
SELECT SUM(total_amount - paid_amount)
FROM orders
WHERE status IN ('signed', 'executing')
```

### 2.3 逾期应收（Overdue Receivables）

**定义**: 超过约定期限未收的款项

**计算逻辑**:
```sql
SELECT SUM(r.total_amount - r.received_amount), COUNT(*)
FROM receivables r
WHERE r.status != 'paid'
  AND r.due_date < CURRENT_DATE
```

### 2.4 应收账龄分析（Aging Analysis）

**定义**: 按逾期天数分段的应收分布

**分段规则**:
- 0-30 天
- 31-60 天
- 61-90 天
- 90 天以上

**计算逻辑**:
```python
today = date.today()
buckets = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}

for receivable in receivables:
    if receivable.status == "paid":
        continue
    overdue_days = (today - receivable.due_date).days
    if overdue_days <= 0:
        bucket = "0-30"
    elif overdue_days <= 30:
        bucket = "0-30"
    elif overdue_days <= 60:
        bucket = "31-60"
    elif overdue_days <= 90:
        bucket = "61-90"
    else:
        bucket = "90+"
    buckets[bucket] += receivable.remaining_amount
```

### 2.5 应收周转天数（Turnover Days）

**定义**: 平均回款周期

**计算逻辑**:
```python
avg_receivable = (期初应收 + 期末应收) / 2
days_in_period = (period_end - period_start).days
turnover_days = (avg_receivable / revenue) * days_in_period if revenue > 0 else 0
```

---

## 3. API 契约

详见 `contracts.md` §1.2

---

## 4. Service 实现

### 4.1 CashflowService

```python
class CashflowService:
    """现金流与应收服务"""

    async def get_metrics(
        self,
        period: PeriodType,
        scope: str,
        user_id: int,
        db: AsyncSession
    ) -> CashflowMetrics:
        """获取现金流指标"""
        period_range = PeriodRange.from_period(period)

        # 并行查询
        cash_in = await self._get_cash_in(period_range, scope, user_id, db)
        receivables = await self._get_receivables_summary(period_range, scope, user_id, db)
        aging = await self._get_aging_analysis(period_range, scope, user_id, db)
        turnover = await self._get_turnover_days(period_range, cash_in.total, db)
        payments = await self._get_payment_summary(period_range, scope, user_id, db)

        return CashflowMetrics(
            period=period,
            cash_in=cash_in,
            receivables=receivables,
            aging=aging,
            turnover_days=turnover,
            payments=payments
        )
```

---

## 5. 缓存策略

- **Key**: `dashboard:cashflow:{period}:{scope}:{user_id}`
- **TTL**: 300 秒

---

## 6. 权限控制

- `dashboard:read` + `finance:read`
- 根据 `scope` 过滤数据

---

## 7. 前端交互

### 7.1 布局

```
┌─────────────────────────────────────────────────────────────┐
│  现金流与应收                                          [本月▼] │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┬──────────┬──────────┬──────────┐             │
│  │ 现金流入 │ 应收余额 │ 逾期应收 │周转天数  │             │
│  │ ¥98.2万 │ ¥32.5万 │ ¥5.8万 🔴│   38天    │             │
│  └──────────┴──────────┴──────────┴──────────┘             │
├─────────────────────────────────────────────────────────────┤
│  付款方式分布              应收账龄分析                       │
│  ┌─────────────────┐    ┌──────────────────────────────────┐│
│  │ ████ 微信 45%   │    │ 30天内  ████████████████ 60%      ││
│  │ ████ 转账 35%   │    │ 31-60天 ██████ 25%                ││
│  │ ██ 现金 15%     │    │ 61-90天 █ 10%                     ││
│  │ █ 其他 5%       │    │ 90天以上 █ 5%                     ││
│  └─────────────────┘    └──────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 7.2 交互规则

- 逾期应收 > 10 万红色标记，> 5 万黄色预警
- 点击"查看逾期应收明细"跳转到应收管理页面

---

## 8. 验收标准

- [ ] 现金流入统计准确，包含各付款方式分布
- [ ] 应收余额 = 订单总额 - 已付金额
- [ ] 逾期应收识别准确
- [ ] 账龄分析分段正确
- [ ] 周转天数计算正确
- [ ] 权限过滤正确
