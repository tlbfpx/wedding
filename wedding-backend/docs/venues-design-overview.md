# Venues 模块设计概览

## 模块职责

Venues 模块负责婚庆管理系统中**场地（婚宴场地/仪式场地）的管理**，包括：

1. 场地的创建、查询、更新（CRUD）
2. 场地可用性查询（查询指定日期范围内已被预订的日期）

该模块与 Events 模块存在关联关系：活动（Event）通过 `venue_id` 关联场地。

## 数据模型

### Venue（场地）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 场地 ID |
| name | str(100) | Unique, NOT NULL | 场地名称 |
| address | str(200) | Nullable | 场地地址 |
| capacity | int | Nullable | 容纳人数 |
| contact | str(50) | Nullable | 联系人 |
| phone | str(20) | Nullable | 联系电话 |
| price | decimal(10,2) | Nullable | 价格 |
| note | text | Nullable | 备注 |
| created_at | datetime | 自动生成 | 创建时间 |
| updated_at | datetime | 自动更新 | 更新时间 |

### 外键关系

- `Event.venue_id` → `Venue.id`：活动关联场地

## 业务规则

### 场地创建

1. 场地名称 `name` 必须唯一，创建时校验重复
2. 除 `name` 外，其余字段均为可选

### 场地更新

1. 仅当 `name` 字段实际发生变更时才校验唯一性（`body.name != venue.name`）
2. 支持部分更新，仅更新传入的非空字段
3. 使用 `model_dump(exclude_unset=True)` 确保只更新用户明确设置的字段

### 场地可用性查询

1. 查询指定日期范围（`date_start` 到 `date_end`）内，该场地关联的非取消状态活动
2. 返回已被占用的日期列表 `booked_dates`
3. 当 `booked_dates` 非空时，`available` 为 `false`
4. 此查询仅作参考，不作为硬性预约约束

### 关键词搜索

支持按 `name`（场地名称）和 `address`（地址）进行模糊匹配搜索，使用 SQL `LIKE` 实现。

### 容量筛选

支持按 `capacity_min` 参数筛选容纳人数大于等于指定值的场地。

### 操作审计

所有写操作（POST/PUT/DELETE）通过 `log_operation` 中间件自动记录操作日志。

## 状态机

Venues 模块无状态机设计。场地本身没有状态字段，场地是否可用取决于关联活动的日期占用情况。
