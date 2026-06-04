# 团队效能功能详细设计

> 功能编号: FH-003
> 所属模块: Dashboard
> 创建日期: 2026-06-04

---

## 1. 功能概述

管理层需要了解团队战斗力：谁在产出、谁的转化高、团队整体效率如何。

---

## 2. 指标定义

### 2.1 团队对比（Team Comparison）

**定义**: 各团队的总营收、人数、人均产出

**计算逻辑**:
```sql
SELECT
    u.team,
    COUNT(DISTINCT u.id) as headcount,
    SUM(o.total_amount) as total_revenue
FROM users u
JOIN orders o ON o.sale_id = u.id
WHERE o.created_at >= :period_start
  AND o.created_at < :period_end
  AND o.status IN ('signed', 'executing', 'completed')
GROUP BY u.team
```

### 2.2 转化漏斗（Conversion Funnel）

**定义**: 客户从接触到签约各环节的转化率

**计算逻辑**:
```sql
SELECT status, COUNT(*)
FROM customers
WHERE created_at >= :period_start
  AND created_at < :period_end
GROUP BY status
```

**转化率计算**:
```python
total = potential + following + intention + signed + lost
funnel = [
    {"stage": "potential", "count": potential, "rate": 1.0},
    {"stage": "following", "count": following, "rate": following / total},
    {"stage": "intention", "count": intention, "rate": intention / total},
    {"stage": "signed", "count": signed, "rate": signed / total},
    {"stage": "lost", "count": lost, "rate": lost / total},
]
```

### 2.3 新增客户（New Customers）

**定义**: 本期新增的潜在客户数

**计算逻辑**:
```sql
SELECT COUNT(*)
FROM customers
WHERE created_at >= :period_start
  AND created_at < :period_end
```

### 2.4 跟进活跃度（Follow-up Activity）

**定义**: 本期跟进记录总数

**计算逻辑**:
```sql
SELECT COUNT(*)
FROM follow_ups
WHERE created_at >= :period_start
  AND created_at < :period_end
```

### 2.5 销售排行（Sales Ranking）

**定义**: 按营收/订单数/转化率排序的销售人员列表

**计算逻辑**:
```sql
SELECT
    u.id as sale_id,
    u.name as sale_name,
    u.team,
    COUNT(o.id) as order_count,
    SUM(o.total_amount) as total_revenue,
    AVG(o.total_amount) as avg_order_value
FROM users u
JOIN orders o ON o.sale_id = u.id
WHERE o.created_at >= :period_start
  AND o.created_at < :period_end
  AND o.status IN ('signed', 'executing', 'completed')
GROUP BY u.id, u.name, u.team
ORDER BY total_revenue DESC
```

**转化率计算**（额外查询）:
```python
for sale in ranking:
    signed_customers = count customers where assigned_sale_id = sale.id and status = 'signed'
    total_customers = count customers where assigned_sale_id = sale.id
    sale.conversion_rate = signed_customers / total_customers if total_customers > 0 else 0
```

---

## 3. API 契约

详见 `contracts.md` §1.3

---

## 4. Service 实现

### 4.1 TeamEfficiencyService

```python
class TeamEfficiencyService:
    """团队效能服务"""

    async def get_metrics(
        self,
        period: PeriodType,
        team: Optional[str],
        page: int,
        page_size: int,
        scope: str,
        user_id: int,
        db: AsyncSession
    ) -> TeamEfficiencyMetrics:
        """获取团队效能指标"""
        period_range = PeriodRange.from_period(period)

        # 并行查询
        teams = await self._get_team_stats(period_range, scope, user_id, db)
        funnel = await self._get_conversion_funnel(period_range, scope, user_id, db)
        new_customers = await self._get_new_customers(period_range, scope, user_id, db)
        follow_up_count = await self._get_follow_up_count(period_range, scope, user_id, db)
        ranking = await self._get_sales_ranking(period_range, team, page, page_size, scope, user_id, db)

        return TeamEfficiencyMetrics(
            period=period,
            teams=teams,
            funnel=funnel,
            new_customers=new_customers,
            follow_up_count=follow_up_count,
            ranking=ranking,
            page=page,
            page_size=page_size,
            total=len(ranking)
        )
```

---

## 5. 缓存策略

- **Key**: `dashboard:team:{period}:{team}:{page}:{scope}:{user_id}`
- **TTL**: 300 秒

---

## 6. 权限控制

- `dashboard:read`
- 根据 `scope` 过滤：
  - `own`: 只看本人数据
  - `team`: 看本团队数据
  - `all`: 看全局数据

---

## 7. 前端交互

### 7.1 布局

```
┌─────────────────────────────────────────────────────────────┐
│  团队效能                                              [本月▼] │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────┬──────────────────────┐ │
│  │  销售团队对比                     │   转化漏斗            │ │
│  │  ┌────────────────────────────┐  │  █████ 潜在 100%      │ │
│  │  │ 销售A组 ████ ¥45.2万 TOP  │  │  ████ 跟进 65%        │ │
│  │  │ 销售B组 ███  ¥38.6万       │  │  ███ 意向 42%        │ │
│  │  │ 销售C组 ██   ¥28.3万 关注 │  │  ██ 签约 27%          │ │
│  │  └────────────────────────────┘  │  █ 流失 5%           │ │
│  └──────────────────────────────────┴──────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  销售排行榜（按营收）                              [按团队▼全部] │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 排名 姓名    团队    订单数  营收    客单价  转化率 跟进数││
│  │  1   张三   销售A组  12    ¥36.8万 ¥3.07万  75%   48   ││
│  │  2   李四   销售A组  10    ¥30.5万 ¥3.05万  70%   42   ││
│  │  3   王五   销售B组   9    ¥28.2万 ¥3.13万  68%   35   ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 7.2 交互规则

- 团队对比条形图，高亮最高和最低
- 转化漏斗百分比展示
- 销售排行榜支持按营收/订单数/转化率排序
- 支持分页加载

---

## 8. 验收标准

- [ ] 团队对比统计准确
- [ ] 转化漏斗各阶段数量正确
- [ ] 转化率计算正确
- [ ] 销售排行排序正确
- [ ] 人均产出 = 团队营收 / 人数
- [ ] 支持按团队筛选
- [ ] 权限过滤正确
