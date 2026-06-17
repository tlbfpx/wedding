## 1. 后端权限点 + 数据迁移

- [ ] 1.1 在权限点定义处（`app/models/permission.py` 或类似）新增 `schedule.delete` 常量（module="schedule", action="delete"）
- [ ] 1.2 创建 Alembic revision `add_schedule_delete_permission.py`，up() 注入 `admin → schedule.delete` 到 `role_permissions` 表，down() 删除该行
- [ ] 1.3 同步更新 `scripts/init_permissions.py`（若存在）追加 `schedule.delete` 到 admin 默认权限列表
- [ ] 1.4 运行 `alembic upgrade head`，验证 `role_permissions` 表中有 `admin → schedule.delete` 行，且 `manager`/`sales`/`planner` 无此权限

## 2. 后端 EventService 删除方法

- [ ] 2.1 在 `app/services/event_service.py` 新增 `async def delete_event(self, event_id: int) -> dict` 方法
- [ ] 2.2 实现逻辑：查 event → 若 status != 'draft' 抛 HTTPException(409, ...)；否则在 `async with db.begin()` 内手动 delete(EventResource) + delete(StaffSchedule) + db.delete(event)
- [ ] 2.3 返回 `{"message": "event deleted", "id": event_id}`

## 3. 后端 Venue 删除（inline 路由）

- [ ] 3.1 在 `app/api/venues.py` 新增 `@router.delete("/{venue_id}")` 路由，加 `require_permission("schedule", "delete")` 依赖
- [ ] 3.2 查询 `count(Event.venue_id == venue_id)`（含所有 status）
- [ ] 3.3 若 count > 0 返回 409，body 含 `referenced_count` 和最多 3 个 `sample_event_ids`（按 Event.date DESC，使用 `select(Event.id).where(...).order_by(Event.date.desc()).limit(3)`）
- [ ] 3.4 若 count == 0，`await db.delete(venue)` 后返回 200 + `{"message": "venue deleted", "id": venue_id}`

## 4. 后端 EventService staff-schedule 创建方法

- [ ] 4.1 在 `app/services/event_service.py` 新增 `async def create_staff_schedule(self, event_id: int, staff_id: int, role: str, date: date) -> StaffSchedule` 方法
- [ ] 4.2 实现：查 event，校验 status ∈ {confirmed, executing}，否则抛 HTTPException(400, current_status=...)
- [ ] 4.3 校验 staff_id 是合法 User（否则 400）
- [ ] 4.4 冲突检测：`select(StaffSchedule, Event).join(...).where(staff_id==x, date==y, event_id != z, status.in_(["assigned","confirmed"]))`，命中抛 HTTPException(409, conflict_event_id=..., conflict_event_title=...)
- [ ] 4.5 插入 StaffSchedule（status='assigned'），flush 后获取 id
- [ ] 4.6 发布 `STAFF_ASSIGNED` 到 event_bus，payload `{staff_id, staff_name, event_id, event_title, role, date}`
- [ ] 4.7 commit，返回创建的 StaffSchedule 记录

## 5. 后端 events 路由（DELETE event + POST staff-schedule）

- [ ] 5.1 在 `app/api/events.py` 新增 `@router.delete("/{event_id}")` 路由，加 `require_permission("schedule", "delete")` 依赖，调用 EventService.delete_event
- [ ] 5.2 在 `app/api/events.py` 新增 `@router.post("/{event_id}/staff-schedule")` 路由，加 `require_permission("schedule", "write")` 依赖，接收 Pydantic body `{staff_id: int, role: str (max 30), date: date}`，调用 EventService.create_staff_schedule

## 6. 后端 Pydantic Schema

- [ ] 6.1 在 `app/schemas/event.py` 新增 `StaffScheduleCreate(BaseModel)`: staff_id: int, role: constr(max_length=30), date: date
- [ ] 6.2 新增 `StaffScheduleResponse(BaseModel)`: id, event_id, staff_id, role, date, status（响应模型）

## 7. 后端事件总线 STAFF_ASSIGNED

- [ ] 7.1 在 `app/events/event_types.py` 新增常量 `STAFF_ASSIGNED = "staff_assigned"`
- [ ] 7.2 在 `app/events/handlers.py` 新增 `async def on_staff_assigned(payload: dict)`，调用 NotificationService.notify_user(staff_id, type="schedule", ...)
- [ ] 7.3 在 event_bus 注册处（main.py 或 event_bus.py 的 subscribe/init 函数）注册 `STAFF_ASSIGNED → on_staff_assigned`

## 8. 后端测试 — conftest 扩展

- [ ] 8.1 在 `tests/conftest.py` 新增 `low_priv_user` fixture：构造只授 `("schedule","read")` 的用户
- [ ] 8.2 新增 `low_priv_client` fixture：参考现有 admin client 的构造方式（注入 JWT/cookie）

## 9. 后端测试 — events 用例（test_events.py）

- [ ] 9.1 `test_delete_draft_event_success`: 创建 draft event + 添加 EventResource + StaffSchedule → DELETE → 200，body 含 id；DB 中 event/resource/schedule 全部消失
- [ ] 9.2 `test_delete_non_draft_event_conflict`: 创建 confirmed event → DELETE → 409，body 含 current_status
- [ ] 9.3 `test_delete_event_forbidden`: low_priv_client DELETE draft event → 403
- [ ] 9.4 `test_create_staff_schedule_success`: 在 confirmed event 上 POST staff-schedule → 200，DB 中 StaffSchedule 存在 status='assigned'
- [ ] 9.5 `test_create_staff_schedule_same_day_conflict`: 先 POST 一个 staff schedule，再 POST 同 staff 同 date 不同 event → 409，body 含 conflict_event_id/title
- [ ] 9.6 `test_create_staff_schedule_completed_not_blocking`: 准备一个 status='completed' 的 StaffSchedule，再 POST 同 staff 同 date → 200（无冲突）
- [ ] 9.7 `test_create_staff_schedule_invalid_event_status`: 在 draft event 上 POST → 400，body 含 current_status
- [ ] 9.8 `test_create_staff_schedule_forbidden`: low_priv_client POST → 403

## 10. 后端测试 — venues 用例（test_venues.py 新建）

- [ ] 10.1 创建 `tests/test_venues.py`
- [ ] 10.2 `test_delete_venue_with_references_conflict`: 创建 venue + 关联 2 个 event（1 confirmed + 1 cancelled）→ DELETE → 409，body referenced_count=2，sample_event_ids 含最多 3 个 id
- [ ] 10.3 `test_delete_venue_without_references_success`: 创建 venue 无任何 event 引用 → DELETE → 200，DB 中消失
- [ ] 10.4 `test_delete_venue_forbidden`: low_priv_client DELETE → 403

## 11. 后端测试 — STAFF_ASSIGNED 事件总线

- [ ] 11.1 `test_staff_assigned_event_published`: mock event_bus.publish，POST staff-schedule 成功 → publish 被调用，payload 含 6 个字段
- [ ] 11.2 `test_staff_assigned_handler_notifies`: 直接调用 `on_staff_assigned(test_payload)`，验证 NotificationService.notify_user 被调用

## 12. 前端 stub 清理

- [ ] 12.1 用 grep 确认 `wedding-frontend/src/views/Events.vue` / `Venues.vue` / `EventDetail.vue` 无任何 import 引用（检查 router/index.ts、views 目录）
- [ ] 12.2 删除 3 个 stub 文件
- [ ] 12.3 运行 `npx vue-tsc --noEmit -p tsconfig.app.json` 验证不引入新 TS 错误
- [ ] 12.4 运行 `npm run build` 验证构建通过

## 13. 文档更新

- [ ] 13.1 在 `docs/events-design-overview.md` 补充 DELETE event 和 POST staff-schedule 章节
- [ ] 13.2 在 `docs/events-contracts.md` 补充两个新端点的完整契约（含请求/响应 body、状态码、错误码）
- [ ] 13.3 在 `docs/venues-design-overview.md` 补充 DELETE venue 章节和引用保护规则
- [ ] 13.4 在 `docs/venues-contracts.md` 补充 DELETE venue 契约
- [ ] 13.5 新建 `docs/changelogs/2026-06-17-scheduling-completion.md`，记录 3 个新端点 + 新权限 + 新事件总线 + 前端清理 + 理由

## 14. 全量验证

- [ ] 14.1 在 `wedding-backend/` 运行 `pytest tests/test_events.py tests/test_venues.py -v` 全绿（原 8 + 新 12 = 20 个用例）
- [ ] 14.2 运行 `pytest tests/ -v`（全量后端测试）确保未破坏现有用例
- [ ] 14.3 在 `wedding-frontend/` 运行 `npx vue-tsc --noEmit -p tsconfig.app.json`，确认无新增 TS 错误
- [ ] 14.4 在 `wedding-frontend/` 运行 `npm run build`，构建产物正常
- [ ] 14.5 启动后端，手动 curl 验证 3 个新端点（DELETE event / DELETE venue / POST staff-schedule）行为符合 spec

## 15. OpenSpec 归档前对齐检查

- [ ] 15.1 验证代码实现与 `specs/schedule-management/spec.md` 中所有 requirement 完全对应（无遗漏、无多余）
- [ ] 15.2 验证测试覆盖 spec 中所有 scenario（每条 WHEN/THEN 至少一个测试）
- [ ] 15.3 验证 `tasks.md` 所有任务全部完成（[x]）
- [ ] 15.4 运行 `openspec validate scheduling-module-completion --strict`（若有该命令）或人工对照 spec 检查代码
