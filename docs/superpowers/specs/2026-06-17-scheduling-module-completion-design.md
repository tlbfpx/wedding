# 排期模块收尾设计 — Scheduling Module Completion

**日期**: 2026-06-17
**作者**: Brainstorming session (Superpowers Phase 1)
**状态**: Confirmed by user — 待写入 OpenSpec

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
- 草稿事件硬删除，**级联清理**其 StaffSchedule、EventResource 记录

**权限**：`events.delete`（新建权限点）

**事件总线**：不发布（草稿无业务影响）

### 3.2 `DELETE /api/v1/venues/{id}` — 引用保护硬删除

**语义**：
- 先查 `count(Event.venue_id == venue.id)` （任何 status）
- 引用数 > 0 → **409 Conflict**，body：
  ```json
  {
    "detail": "venue is referenced by events",
    "referenced_count": 5,
    "sample_event_ids": [12, 34, 56]
  }
  ```
- 引用数 == 0 → 硬删除

**权限**：`venues.delete`（新建权限点）

### 3.3 `POST /api/v1/events/{id}/staff-schedule` — 单条排班创建

**请求 body**：
```json
{
  "staff_id": 7,
  "role": "planner",
  "date": "2026-07-15"
}
```

**语义**：
1. 校验 event 存在 + status ∈ {confirmed, executing}（draft/cancelled/completed 拒绝）
2. 校验 staff_id 是合法 User
3. **冲突检测**：`StaffSchedule.staff_id == body.staff_id AND date == body.date AND event_id != body.event_id AND status='assigned'`
   - 命中 → **409 Conflict**，body 含 `{ "conflict_event_id": N, "conflict_event_title": "..." }`
4. 插入 StaffSchedule（status='assigned'），返回 **201 Created** + 创建的记录
5. 发布事件总线 `STAFF_ASSIGNED`，handler 通知该 staff（与现有 `EVENT_CREATED` 模式一致）

**权限**：`events.manage`（复用现有）

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

---

## 6. 数据迁移

新增 2 个权限点种子数据：
- `events.delete`
- `venues.delete`

通过 Alembic data migration 注入到默认角色（`admin` 默认拥有，`manager` 视情况）。

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
