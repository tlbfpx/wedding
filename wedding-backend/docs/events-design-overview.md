# Events 模块设计概览

## 模块职责

Events 模块负责婚庆管理系统中**活动（婚礼/活动）的全生命周期管理**，包括：

1. 活动的创建、查询、更新（CRUD）
2. 活动资源分配与管理（人员、场地、车辆、设备等）
3. 员工排班查询
4. 场地和人员冲突检测

该模块是系统的核心调度模块，与订单模块（Orders）、用户模块（Users）、场地模块（Venues）存在依赖关系。

## 数据模型

### Event（活动）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 活动 ID |
| order_id | int | FK(orders.id), Unique, Nullable | 关联订单 ID |
| title | str(100) | NOT NULL | 活动标题 |
| date | date | NOT NULL | 活动日期 |
| start_time | time | Nullable | 开始时间 |
| end_time | time | Nullable | 结束时间 |
| venue_id | int | FK(venues.id), Nullable | 场地 ID |
| status | EventStatus | 默认 draft | 活动状态 |
| planner_id | int | FK(users.id), Nullable | 策划师 ID |
| note | text | Nullable | 备注 |
| created_at | datetime | 自动生成 | 创建时间 |
| updated_at | datetime | 自动更新 | 更新时间 |

### EventResource（活动资源）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 资源 ID |
| event_id | int | FK(events.id), NOT NULL | 所属活动 ID |
| resource_type | ResourceType | NOT NULL | 资源类型 |
| resource_id | int | NOT NULL | 资源实体 ID（多态关联） |
| quantity | int | 默认 1 | 数量 |
| note | str(200) | Nullable | 备注 |

### StaffSchedule（员工排班）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, 自增 | 排班 ID |
| staff_id | int | FK(users.id), NOT NULL | 员工 ID |
| event_id | int | FK(events.id), NOT NULL | 活动 ID |
| role | str(30) | NOT NULL | 员工在活动中的角色（如"摄影师"、"化妆师"） |
| date | date | NOT NULL | 排班日期 |
| status | ScheduleStatus | 默认 assigned | 排班状态 |

### 枚举类型

**EventStatus（活动状态）**：

| 值 | 说明 |
|------|------|
| draft | 草稿 |
| confirmed | 已确认 |
| executing | 执行中 |
| completed | 已完成 |
| cancelled | 已取消 |

**ResourceType（资源类型）**：

| 值 | 说明 |
|------|------|
| staff | 人员 |
| venue | 场地 |
| vehicle | 车辆 |
| equipment | 设备 |
| other | 其他 |

**ScheduleStatus（排班状态）**：

| 值 | 说明 |
|------|------|
| assigned | 已分配 |
| confirmed | 已确认 |
| completed | 已完成 |

## 业务规则

### 活动创建

1. 活动日期 `date` 为必填字段（支持 `date` 或 `event_date` 两种参数名传入）
2. 创建时自动触发场地冲突检测：同一天同一场地不允许存在多个非取消状态的活动
3. 新建活动状态固定为 `draft`，不可通过创建接口指定其他状态

### 活动更新

1. 仅在修改 `date` 或 `venue_id` 时触发冲突检测
2. 冲突检测会排除当前活动自身（`exclude_event_id`），避免自身冲突误判
3. 支持部分更新，仅更新传入的字段

### 资源管理

1. `EventResource` 使用多态关联设计，`resource_type` + `resource_id` 可关联不同类型的资源实体
2. 添加资源时验证活动是否存在
3. 删除资源时验证资源是否属于指定活动

### 排班管理

1. `StaffSchedule` 通过 `staff_id` 关联用户，通过 `event_id` 关联活动
2. `role` 为自由文本字段，记录员工在具体活动中的职责角色
3. 排班支持按日期、员工、活动多维度查询

### 冲突检测

1. **场地冲突**：同一天同一场地不允许存在多个非 `cancelled` 状态的活动
2. **人员冲突**：同一天同一员工不允许被分配到多个活动的排班中
3. 冲突检测支持排除指定活动（用于更新场景）

### 操作审计

所有写操作（POST/PUT/DELETE）通过 `log_operation` 中间件自动记录操作日志，包括操作人、操作类型、目标路径、详细信息和客户端 IP。

## 状态机

### 活动状态流转

```
draft ──→ confirmed ──→ executing ──→ completed
  │                                     
  └──→ cancelled                        
```

- `draft`（草稿）→ `confirmed`（已确认）：策划方案确认后手动触发
- `confirmed` → `executing`（执行中）：活动当天或开始执行时触发
- `executing` → `completed`（已完成）：活动结束后手动触发
- `draft` / `confirmed` → `cancelled`（已取消）：取消活动时触发
- 当前代码未对状态流转做强制约束，任何状态都可以通过更新接口直接设置

### 排班状态流转

```
assigned ──→ confirmed ──→ completed
```

- `assigned`（已分配）→ `confirmed`（已确认）：员工确认可参加
- `confirmed` → `completed`（已完成）：活动结束后确认完成
