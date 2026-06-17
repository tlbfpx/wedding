## Context

排期模块（schedule-management）当前实现度约 75–80%：核心 CRUD、冲突检测、日历 UI、场地档期查询全部上线，13 个 API 端点 + 8 个测试用例覆盖主路径。但缺少 3 个端点（草稿事件删除、场地删除、staff 排班创建）使得模块无法称为"API 完整"，前端还遗留 3 个未使用的根目录 stub Vue 文件。

经 brainstorming 探索 + 2 轮 oracle spec review，4 个关键设计决策已锁定：
1. Event 删除用状态驱动（仅 draft 可删，非草稿走 PUT status=cancelled）
2. Venue 删除用引用保护硬删（含 cancelled 事件）
3. StaffSchedule 创建单条 + 同日严格冲突（{assigned,confirmed} 阻塞，completed 不阻塞）
4. 前端仅清理 stub，不加新 UI

详细 brainstorming 过程见 `docs/superpowers/specs/2026-06-17-scheduling-module-completion-design.md`。

**技术约束**：
- 现有权限用 2-arg 模式 `require_permission(module, action)`（非 flat string）
- `EventResource.event_id` / `StaffSchedule.event_id` 的 ForeignKey 无 `ondelete` 子句，ORM relationship 无 `cascade="all, delete-orphan"`
- `ScheduleStatus` 枚举有 3 个值：`assigned` / `confirmed` / `completed`
- 现有 POST 端点（create_event / add_resource）返回 200，DELETE 端点（remove_resource）返回 200 + `{"message":...}`

## Goals / Non-Goals

**Goals:**
- 补齐 3 个缺失端点，达到 API 完整性
- 复用现有 `("schedule", "delete")` 2-arg 权限模式，admin 角色自动获得
- 触发 `STAFF_ASSIGNED` 事件总线通知 staff（与 `EVENT_CREATED` 通知销售/策划师模式一致）
- 清理 3 个废弃前端 stub 文件
- TDD 全程测试覆盖（5 + 2 + 3 个权限用例 = 10 个新测试）

**Non-Goals:**
- 不引入软删除/回收站（Event 草稿无业务关联，Venue 用引用保护足够）
- 不加 staff 指派/取消事件/删除草稿的前端 UI（YAGNI，留作后续 change）
- 不引入 VenueService（保持现有 inline 实现）
- 不修改 Event/Venue schema 结构
- 不加 Timeline/甘特图视图
- 不加批量排班 API

## Decisions

### D1：Event 删除用状态驱动而非软删除

**选择**：DELETE 端点仅允许 `status='draft'`，非草稿返回 409 提示用 PUT 改 `status='cancelled'`

**理由**：Event 已有 5 个状态（draft/confirmed/executing/completed/cancelled），取消走已有 PUT 即可。Customer 用 `recycled_at` 软删除是因为客户是公司资产（复购、再激活、合规审计），但 Event 是一次性活动，草稿没业务关联，无需回收站。

**替代方案考虑**：
- 软删除 + 回收站（被否）：需新增字段 + restore 端点 + 列表过滤逻辑，改动面大且无 ROI
- 硬删除任意状态（被否）：confirmed/executing/completed 事件有 StaffSchedule、Payment 关联，硬删会留下孤儿记录

### D2：Venue 删除用引用保护硬删除（含 cancelled 事件）

**选择**：先查 `count(Event.venue_id == venue.id)` 包含所有 status（含 cancelled），引用 > 0 返回 409 带 `referenced_count` 和最多 3 个 sample event id（按 date DESC），引用 == 0 硬删

**理由**：
- 含 cancelled 是为了保护历史审计记录（一场已取消的活动仍占用了场地的历史档期，不应让场地被悄悄删除）
- 上限 3 个 sample event id 是平衡响应体积与可操作性，最近日期优先便于用户排查

**替代方案考虑**：
- 排除 cancelled（被否）：会让 cancelled 事件的场地被删后产生悬空引用
- 软删除 + is_active 停用（被否）：增加查询复杂度，且场地是基础数据不应"已删除但仍存在"

### D3：StaffSchedule 创建用单条 + 同日严格冲突

**选择**：单条创建（一次一个 staff），冲突检测覆盖 `status ∈ {assigned, confirmed}`，不含 `completed`

**理由**：
- 单条而非批量：错误响应清晰（每个 409 直接对应一个 staff），实现简单，符合 REST 资源语义
- `{assigned, confirmed}` 都阻塞：两者都是"该 staff 已被锁定到那个 event"
- `completed` 不阻塞：staff 当天已完成另一个活动，当天晚些时间或同时段不同角色可再分配

**替代方案考虑**：
- 批量 + 部分成功返回（被否）：语义复杂，前端难处理，事务边界模糊
- 单条 + 冲突可覆盖标志（被否）：可能被误用，破坏排期一致性

### D4：级联清理用事务内手动删除而非 schema 迁移

**选择**：在 EventService 的 `delete_event` 方法内，事务包裹手动删除 StaffSchedule + EventResource + Event

**理由**：现有 ForeignKey 无 `ondelete` 子句，修改 schema 需 Alembic 迁移 + 风险评估。手动删除代码可控、易测试、可回滚。

**代码骨架**：
```python
async with db.begin():
    await db.execute(delete(EventResource).where(EventResource.event_id == event_id))
    await db.execute(delete(StaffSchedule).where(StaffSchedule.event_id == event_id))
    await db.delete(event)
```

**替代方案考虑**：
- Alembic 加 ON DELETE CASCADE（被否）：DB 层级联一旦配置错误不可逆，且需停机迁移
- ORM `cascade="all, delete-orphan"`（被否）：仅在 ORM 层生效，DB 层 FK 仍无保护，迁移到其他客户端会失败

### D5：权限用 `("schedule", "delete")` 2-arg 模式

**选择**：新增 `module="schedule", action="delete"` 权限点，复用现有 `require_permission("schedule", "delete")` 模式

**理由**：现有代码全部用 2-arg 模式（`("schedule","read")`、`("schedule","write")`），flat string 会破坏 RBAC loader。

**角色分配**：
- admin → 授予（破坏性操作应有最高权限）
- manager → **不授予**（DELETE 是不可恢复操作，admin-only 更安全）
- sales / planner → 不授予

### D6：STAFF_ASSIGNED 事件总线（staff-centric payload）

**选择**：新增 `STAFF_ASSIGNED = "staff_assigned"` 常量，handler `on_staff_assigned` 调用 `NotificationService.notify_user(staff_id, ...)`，payload 6 字段 `{staff_id, staff_name, event_id, event_title, role, date}`

**理由**：现有 `EVENT_CREATED` payload 是 event-centric（含 order_id、planner_id），但 staff 通知需要 staff-centric 信息（你是谁、被指派到哪场、什么角色、哪天）。两者结构不同，强行复用会导致 handler 解析混乱。

**替代方案考虑**：
- 复用 EVENT_CREATED payload（被否）：handler 需要二次查找 staff 信息，违反单一职责
- 不发通知（被否）：staff 不知道自己被指派，需要人工同步，违反事件驱动设计原则

### D7：状态码统一用 200 + message body

**选择**：所有新端点返回 200 OK + `{"message": ..., ...}` body

**理由**：现有 `create_event`（POST 返回 200）、`add_resource`（POST 返回 200）、`remove_resource`（DELETE 返回 200 + message）都遵循此模式。REST 纯粹派会偏好 201/204，但项目一致性优先。

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| 手动级联删除事务失败导致孤儿记录 | 单元测试覆盖事务回滚；EventService `delete_event` 用 `async with db.begin()` 保证原子性 |
| `schedule.delete` 权限未被任何角色持有导致 403 死锁 | Alembic data migration 确定性注入 admin；脚本同步更新 `scripts/init_permissions.py`；集成测试验证 admin 可访问 |
| Event 选硬删除与 Customer 软删除不一致引发使用者困惑 | changelog 明确说明 Event 草稿无业务关联属性，无需回收站 |
| StaffSchedule 创建触发 staff 同日 confirmed 冲突被误判 | 错误 body 含 `conflict_event_id` + `conflict_event_title`，前端可直接展示冲突源 |
| `completed` 不阻塞导致同一天 staff 被多次分配 | 设计如此（已完成活动不阻塞当天后续指派）；若实际场景需要阻塞，下个 change 加配置开关 |
| Alembic migration 顺序问题（FK CASCADE vs permission seed 若同时做）| 本 change 不修改 FK，只做 permission seed，单一 revision，无顺序冲突 |
| `manager` 角色不授予 `schedule.delete` 影响日常运营 | changelog 显式提示；如需开放，下个 change 评估 |

## Migration Plan

**部署步骤**：
1. 后端代码合并到主分支（含 3 个新端点 + EventService 新方法 + event_bus handler）
2. Alembic upgrade head（注入 `schedule.delete` 权限到 admin）
3. 重启后端服务（订阅 `STAFF_ASSIGNED` handler）
4. 前端清理 stub 文件 + 重新构建部署

**回滚策略**：
- 代码层面：`git revert` merge commit，无 schema 变更无需回滚 DB
- 权限层面：删除 `role_permissions` 表中 `permission_code='schedule.delete'` 的行（可选，留作无害）
- 数据层面：本变更不修改任何业务数据，无数据回滚需求

**零停机**：3 个新端点纯增量，不影响现有路径；权限点缺失仅导致新端点 403，旧端点不受影响。
