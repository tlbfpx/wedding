# 排期模块收尾设计 — Scheduling Module Completion

**日期**: 2026-06-17
**作者**: Brainstorming session (Superpowers Phase 1)
**状态**: Confirmed by user, reviewed by oracle (1 fix round applied) — 待写入 OpenSpec

---

## 1. 背景与动机

排期模块（Event / Venue / EventResource / StaffSchedule）经审计实现度约 75–80%。核心路径（日历→活动→场地→冲突检测）前后端均在线，但 API 层存在 3 处缺口，前端存在 3 个废弃 stub 文件：

**缺口清单**：
1. ❌ `DELETE /api/v1/events/{id}` — 事件删除端点缺失
2. ❌ `DELETE /api/v1/venues/{id}` — 场地删除端点缺失
3. ❌ `POST /api/v1/events/{id}/staff-schedule` — 排班创建 API 缺失（目前只能直连 DB）
4. 🧹 `src/views/Events.vue` / `Venues.vue` / `EventDetail.vue` — 3 个根目录 stub 已被 router 绕过

本设计目标是**收尾**这 4 项，让排期模块达到 API 完整性，便于后续生产使用。

不在范围内：批量排班、软删除回收站、staff 指派 UI、Timeline/甘特图视图、schema 结构调整。

---

## 2. 设计决策（已与用户确认）

| # | 决策点 | 选择 | 理由 |
|---|---|---|---|
| Q1 | Event 删除策略 | **B. 状态驱动** | 复用现有 5 个 status，取消走 PUT；DELETE 仅清理草稿，避免误删有业务关联的事件 |
| Q2 | Venue 删除策略 | **A. 引用保护硬删除** | Venue 是基础数据；有 Event 引用时拒绝，无引用时硬删，简单安全 |
| Q3 | StaffSchedule 创建语义 | **A. 单条 + 同日严格冲突** | 一次一个 staff，同日跨 event 冲突即拒绝，错误明确 |
| Q4 | 前端范围 | **A. 仅清理 stub** | 后端 API 优先，UI 留作后续 change |

---

## 3. 后端变更

### 3.1 `DELETE /api/v1/events/{id}` — 草稿清理

**语义**：
- 仅允许 `status='draft'` 的事件被删除
- 非草稿状态（confirmed / executing / completed / cancelled）→ 返回 **409 Conflict**，body 提示用 `PUT /events/{id}` 改 `status='cancelled'`
- 草稿事件硬删除

**级联清理（事务内手动删除）**：
现有 `EventResource.event_id` 和 `StaffSchedule.event_id` 的 ForeignKey 无 `ondelete` 子句，ORM relationship 也无 `cascade="all, delete-orphan"`。**采用事务内手动删除**（不修改 schema，避免迁移风险）：
```python
async with db.begin():
    await db.execute(delete(EventResource).where(EventResource.event_id == event_id))
    await db.execute(delete(StaffSchedule).where(StaffSchedule.event_id == event_id))
    await db.delete(event)
```

**成功响应**：返回 **200 OK** + `{"message": "event deleted", "id": <id>}`（与现有 `remove_resource` 风格一致）

**权限**：`require_permission("schedule", "delete")`（新建 2-arg 权限，与现有 `("schedule","read")` / `("schedule","write")` 模式一致）

**事件总线**：不发布（草稿无业务影响）

### 3.2 `DELETE /api/v1/venues/{id}` — 引用保护硬删除

**语义**：
- 先查 `count(Event.venue_id == venue.id)` （**包含所有 status，包括 cancelled**，以保护历史审计记录）
- 引用数 > 0 → **409 Conflict**，body：
  ```json
  {
    "detail": "venue is referenced by events",
    "referenced_count": 5,
    "sample_event_ids": [12, 34, 56]
  }
  ```
  `sample_event_ids`：最多 3 个，按 `Event.date DESC` 排序（最近的）
- 引用数 == 0 → 硬删除

**成功响应**：返回 **200 OK** + `{"message": "venue deleted", "id": <id>}`（与 events 一致）

**权限**：`require_permission("schedule", "delete")`（与 events.delete 复用同一权限点）

**实现位置**：现有 `venues.py` router 是 inline 实现（无 VenueService）。本次保持 inline，不引入 VenueService（YAGNI）。

### 3.3 `POST /api/v1/events/{id}/staff-schedule` — 单条排班创建

**请求 body**：
```json
{
  "staff_id": 7,
  "role": "策划师",
  "date": "2026-07-15"
}
```

**字段约束**：
- `role`：自由字符串，max 30 字符，无枚举（与现有 `StaffSchedule.role String(30)` 一致；现有测试用 `"策划师"` / `"司仪"`）
- `date`：可独立于 `Event.date`（允许排班到 prep day / post day，不强制等于事件日期）

**语义**：
1. 校验 event 存在 + `status ∈ {confirmed, executing}`（draft/cancelled/completed 返回 400 拒绝）
2. 校验 staff_id 是合法 User（否则 400）
3. **冲突检测**：
   ```python
   conflict = await db.execute(
       select(StaffSchedule, Event).join(Event, Event.id == StaffSchedule.event_id)
       .where(
           StaffSchedule.staff_id == body.staff_id,
           StaffSchedule.date == body.date,
           StaffSchedule.event_id != body.event_id,
           StaffSchedule.status.in_(["assigned", "confirmed"])  # 不包含 completed
       )
   )
   ```
   - 命中 → **409 Conflict**，body 含 `{ "conflict_event_id": N, "conflict_event_title": "..." }`
   - **`completed` 状态不阻塞**（历史记录，staff 当天实际已完成且现在空闲）
4. 插入 StaffSchedule（status='assigned'），返回 **200 OK** + 创建的记录（与现有 `create_event`/`add_resource` 返回 200 一致）
5. **事件总线发布**（详见 §3.3.1）

**权限**：`require_permission("schedule", "write")`（复用现有，不新建）

#### 3.3.1 STAFF_ASSIGNED 事件总线

- 在 `app/events/event_types.py` 新增常量：`STAFF_ASSIGNED = "staff_assigned"`
- 在 `app/events/handlers.py` 新增 handler `on_staff_assigned(payload)`：
  - payload 形状（与 EVENT_CREATED 不同，因为是 staff-centric）：
    ```python
    {
      "staff_id": 7,
      "staff_name": "张三",
      "event_id": 12,
      "event_title": "王先生婚礼",
      "role": "策划师",
      "date": "2026-07-15"
    }
    ```
  - 调用 `NotificationService.notify_user(staff_id, ...)` 生成 `schedule` 类型通知（与现有 `on_event_created` 调用 NotificationService 的方式一致）
- 在 `app/events/event_bus.py`（或 main.py 启动注册处）注册 `STAFF_ASSIGNED → on_staff_assigned`

---

## 4. 前端变更（仅清理）

删除 3 个根目录 stub 文件：
- `wedding-frontend/src/views/Events.vue`
- `wedding-frontend/src/views/Venues.vue`
- `wedding-frontend/src/views/EventDetail.vue`

**前置校验**：删除前用 `grep -r "views/Events\|views/Venues\|views/EventDetail"` 确认无 import 引用（路由已绕过它们指向 `views/events/EventList.vue` 等）。

**不加任何新 UI**（Q4=A）。

---

## 5. 测试策略（TDD）

按 `tests/test_events.py`（已有 8 个测试）的风格补充：

### 5.1 `tests/test_events.py` 新增用例

| 测试名 | 覆盖 |
|---|---|
| `test_delete_draft_event_success` | 删 draft event，记录消失，StaffSchedule+EventResource 级联清理 |
| `test_delete_non_draft_event_conflict` | 删 confirmed event → 409，提示用 PUT 取消 |
| `test_create_staff_schedule_success` | 创建成功 → 201，DB 有记录 |
| `test_create_staff_schedule_same_day_conflict` | 同 staff 同日跨 event → 409，body 含冲突 event 信息 |
| `test_create_staff_schedule_invalid_event_status` | draft/cancelled event 上创建排班 → 400 |

### 5.2 `tests/test_venues.py`（新建文件）

| 测试名 | 覆盖 |
|---|---|
| `test_delete_venue_with_references_conflict` | 有 Event 引用 → 409，body 含 referenced_count + sample_event_ids |
| `test_delete_venue_without_references_success` | 无引用 → 204，DB 中消失 |

### 5.3 权限测试

每个新端点加一个 403 用例（无权限用户访问）。

**前置工作**：现有 `tests/conftest.py` 无 low-privilege user fixture（test_events.py 历史 0 个 403 测试）。需扩展 conftest：
- 新增 `low_priv_user` fixture：授予 `("schedule","read")` 但不授 `("schedule","write")` / `("schedule","delete")`
- 新增对应 auth client fixture（参考现有 admin client 的构造方式）

---

## 6. 数据迁移

新增 1 个权限点（两个 DELETE 端点共用）：
- module=`schedule`, action=`delete` (code=`schedule.delete`)

通过 Alembic data migration 注入。**确定性种子**：
- `admin` 角色 → 授予 `schedule.delete` ✅
- `manager` 角色 → **不授予**（DELETE 是破坏性操作，admin-only 更安全）
- `sales` / `planner` 角色 → 不授予

Alembic migration 文件路径：`wedding-backend/alembic/versions/<rev>_add_schedule_delete_permission.py`（具体 rev id 由 alembic revision 生成）。同时在权限初始化的 seed 脚本（若有 `scripts/init_permissions.py` 或类似）中追加该权限点。

---

## 7. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 硬删草稿事件级联失败 | 测试覆盖 StaffSchedule + EventResource 级联清理；事务包裹 |
| 新权限点未被任何角色持有 | Alembic 迁移注入 admin；文档明确说明 |
| Event 选用硬删除与 Customer 软删除模式不一致 | changelog 注明：Event 草稿无业务关联，无需回收站；Customer 有客户资产属性 |
| StaffSchedule 创建触发 staff 同日冲突 | 同日严格冲突策略（Q3=A），错误 body 含冲突 event 信息，便于前端引导用户改期 |

---

## 8. 不在范围内（YAGNI）

- ❌ 批量排班 API（Q3=B 已排除）
- ❌ 软删除 + 回收站（Q1/Q2 已排除）
- ❌ StaffSchedule 批量更新 / 删除端点
- ❌ Staff 指派 / 取消事件 / 删除草稿的前端 UI（Q4 已排除）
- ❌ Timeline / 甘特图视图
- ❌ Event / Venue schema 结构调整
- ❌ 独立的场地日历视图（按场地看所有排期）

这些可在后续 OpenSpec change 中处理。

---

## 9. 验收标准（OpenSpec tasks 完成判据）

1. ✅ 3 个新端点全部实现并通过集成测试
2. ✅ 2 个新权限点注入并测试
3. ✅ 3 个 stub 文件已删除，前端 build 通过
4. ✅ `pytest tests/test_events.py tests/test_venues.py` 全绿
5. ✅ `vue-tsc --noEmit` 不引入新 TS 错误
6. ✅ changelog 文档已更新
7. ✅ OpenSpec artifacts（proposal/design/spec/tasks）齐全且对齐
