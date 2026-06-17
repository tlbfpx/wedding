## Why

排期模块（schedule-management）当前 API 实现度约 75–80% — 核心 CRUD、冲突检测、日历 UI、场地档期查询均在线，但缺少 3 个 API 端点（`DELETE /events/{id}`、`DELETE /venues/{id}`、`POST /events/{id}/staff-schedule`）和 3 个被 router 绕过的根目录 stub 文件。当前只能通过直连数据库创建 StaffSchedule，无法删除草稿事件或场地，阻塞模块投入生产使用。本次变更收尾这些缺口，使排期模块达到 API 完整性。

## What Changes

- **新增 `DELETE /api/v1/events/{id}`**：仅允许删除 `status='draft'` 的事件，事务内手动级联清理 StaffSchedule 和 EventResource；非草稿返回 409 提示用 `PUT` 改 `status='cancelled'`
- **新增 `DELETE /api/v1/venues/{id}`**：引用保护硬删除，若任何 Event 引用此场地（任何 status，含 cancelled）则返回 409 带 `referenced_count` 和最多 3 个 sample event id（按 date DESC）
- **新增 `POST /api/v1/events/{id}/staff-schedule`**：单条排班创建，同日同 staff 跨 event 冲突严格拒绝（含 `status ∈ {assigned, confirmed}`，不含 `completed`）
- **新增权限点** `schedule.delete`（2-arg `(module="schedule", action="delete")`），admin 角色授予，manager 不授予
- **新增事件总线** `STAFF_ASSIGNED`，handler 通知被指派的 staff
- **删除 3 个废弃 stub 文件**：`wedding-frontend/src/views/Events.vue`、`Venues.vue`、`EventDetail.vue`（已被 `views/events/{EventList,EventDetail,VenueList}.vue` 替代）

## Capabilities

### New Capabilities

无。所有变更都落在已有的 `schedule-management` capability 内。

### Modified Capabilities

- `schedule-management`: 新增 3 个端点行为（草稿删除、场地引用保护删除、staff 排班创建 + 同日冲突），新增权限点 `schedule.delete`，新增事件总线 `STAFF_ASSIGNED`

## Impact

- **后端 API**：
  - `wedding-backend/app/api/events.py` — 新增 DELETE event + POST staff-schedule 路由
  - `wedding-backend/app/api/venues.py` — 新增 DELETE venue 路由
  - `wedding-backend/app/services/event_service.py` — 新增 `delete_event` / `create_staff_schedule` 方法（含事务、级联、冲突检测）
- **后端事件总线**：
  - `wedding-backend/app/events/event_types.py` — 新增 `STAFF_ASSIGNED` 常量
  - `wedding-backend/app/events/handlers.py` — 新增 `on_staff_assigned` handler
  - `wedding-backend/app/main.py`（或 event_bus 注册处）— 订阅 `STAFF_ASSIGNED → on_staff_assigned`
- **后端数据迁移**：
  - 新 Alembic revision 注入权限点 `schedule.delete` 到 `role_permissions` 表
  - 同步更新 `scripts/init_permissions.py`（若存在）
- **前端清理**：
  - 删除 3 个未使用 stub Vue 文件（router 已绕过）
  - 不加任何新 UI（YAGNI）
- **测试**：
  - `wedding-backend/tests/test_events.py` — 新增 5 个用例（删 draft、非 draft 409、staff 创建成功、同日冲突、invalid event status）
  - `wedding-backend/tests/test_venues.py`（**新建**） — 2 个用例（引用保护 409、无引用成功）
  - `wedding-backend/tests/conftest.py` — 新增 `low_priv_user` fixture 支持 403 测试
- **文档**：
  - `docs/events-design-overview.md` / `docs/events-contracts.md` — 补充 3 个新端点
  - `docs/venues-design-overview.md` / `docs/venues-contracts.md` — 补充 DELETE venue
  - 新增 `docs/changelogs/2026-06-17-scheduling-completion.md`
- **权限影响**：现有 admin 角色自动获得 `schedule.delete`；其他角色需显式授予
- **兼容性**：纯新增端点 + 1 个权限点，无 breaking change
