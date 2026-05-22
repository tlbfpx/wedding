# FR-013: 数据报表导出

> 优先级：P0
> 所属模块：报表中心
> 关联用户故事：US-001, US-002
> 状态：待开发

---

## 功能描述

支持将系统中的业务数据导出为 Excel 文件，供管理层进行离线分析和汇报。涵盖订单报表、客户报表、财务报表三类核心报表，支持按时间范围和筛选条件导出。

---

## 输入

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| report_type | string | 是 | 报表类型：order / customer / finance |
| date_start | string | 否 | 开始日期（YYYY-MM-DD），默认本月1号 |
| date_end | string | 否 | 结束日期（YYYY-MM-DD），默认今天 |
| status | string | 否 | 状态筛选（各报表含义不同） |
| sale_id | int | 否 | 销售ID筛选 |

---

## 输出

返回 Excel 文件（.xlsx），Content-Type 为 `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`。

### 订单报表列

| 列名 | 来源 |
|------|------|
| 订单编号 | order.order_no |
| 客户姓名 | customer.name |
| 销售 | sale_user.name |
| 策划师 | planner_user.name |
| 订单状态 | order.status（中文映射） |
| 订单总额 | order.total_amount |
| 已付金额 | order.paid_amount |
| 折扣 | order.discount |
| 创建时间 | order.created_at |

### 客户报表列

| 列名 | 来源 |
|------|------|
| 客户姓名 | customer.name |
| 手机号 | customer.phone |
| 状态 | customer.status（中文映射） |
| 来源 | customer.source |
| 预算范围 | customer.budget_range |
| 婚期 | customer.wedding_date |
| 负责销售 | sale_user.name |
| 跟进次数 | COUNT(follow_ups) |
| 最近跟进 | MAX(follow_up.created_at) |
| 创建时间 | customer.created_at |

### 财务报表列

| 列名 | 来源 |
|------|------|
| 订单编号 | order.order_no |
| 客户姓名 | customer.name |
| 付款方式 | payment.method（中文映射） |
| 付款金额 | payment.amount |
| 付款时间 | payment.paid_at |
| 订单总额 | order.total_amount |
| 已付总额 | order.paid_amount |
| 待付金额 | order.total_amount - order.paid_amount |

---

## 业务规则

1. 导出数据上限 10000 条，超出提示用户缩小筛选范围
2. 文件名格式：`{report_type}_{YYYYMMDD_HHmmss}.xlsx`
3. 订单状态、客户状态、付款方式等枚举值导出时转为中文
4. 仅管理员和销售主管可导出财务报表
5. 所有已登录用户可导出订单和客户报表

---

## 异常场景

| 场景 | 触发条件 | 处理方式 |
|------|----------|----------|
| 无数据 | 筛选结果为空 | 返回空 Excel（仅表头） |
| 数据量过大 | 超过 10000 条 | 返回 400 提示缩小范围 |
| 权限不足 | 非管理员导出财务报表 | 返回 403 |

---

## 验收标准

| 编号 | 验收条件 | 验证方式 |
|------|----------|----------|
| AC-001 | 导出订单报表，字段完整且状态为中文 | 导出并检查 Excel 内容 |
| AC-002 | 导出客户报表，包含跟进统计列 | 导出并检查 |
| AC-003 | 导出财务报表，付款明细正确 | 导出并核对金额 |
| AC-004 | 筛选条件生效，导出数据符合筛选 | 按日期范围导出验证 |
| AC-005 | 空数据导出返回仅含表头的 Excel | 用不存在的筛选条件导出 |
| AC-006 | 超过 10000 条返回友好错误 | 设置大范围日期导出 |
