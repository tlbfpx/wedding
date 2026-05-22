# 研发生命周期跟踪

> 分支名称：refactor/extract-service-layer-decouple-approval
> 需求规模：大型改造
> 迭代目标：提取 Service 层、解耦审批-订单、引入领域事件
> 创建日期：2026-05-22
> 最后更新：2026-05-22

---

## 1. 阶段总览

| Phase | 阶段名称 | 状态 | 人工确认 | 开始时间 | 完成时间 | 备注 |
|-------|----------|------|----------|----------|----------|------|
| 0 | 基线建档 | 跳过 | - | | | 已在 docs/baseline-documentation 分支完成 |
| 1 | 需求分析与 PRD | 跳过 | - | | | 本次为技术重构，无需 PRD |
| 2 | 交互设计 | 跳过 | - | | | 不涉及 UI 变更 |
| 3 | 架构设计 | 已完成 | 已通过 | 2026-05-22 | 2026-05-22 | docs/refactoring-plan.md |
| 4 | 并行开发 | 已完成 | - | 2026-05-22 | 2026-05-22 | 17 commits, 全部 API 验证通过 |
| 5 | 集成测试 | 进行中 | - | 2026-05-22 | | 核心 API + 审批-订单解耦验证通过 |

**状态说明**：未开始 → 进行中 → 待确认 → 已完成 / 跳过

---

## 2. 团队分配

### 角色分配

| 角色 | Agent 名称 | 状态 | 负责阶段 |
|------|-----------|------|----------|
| Team Lead | claude (主 agent) | 进行中 | 全流程协调 |
| 后端架构师 | architect | 已完成 | Phase 3 |
| 后端开发工程师 1 | backend-dev-1 | 已完成 | Phase 4（OrderService, ApprovalService） |
| 后端开发工程师 2 | backend-dev-2 | 已完成 | Phase 4（CustomerService, EventService） |
| 后端开发工程师 3 | backend-dev-3 | 已完成 | Phase 4（SupplierService, UserService） |

### Phase 4 模块开发进度

| 模块 | 负责人 | 总任务数 | 已完成 | 进度 | 当前任务 |
|------|--------|----------|--------|------|----------|
| 基础设施 | Team Lead | 2 | 0 | 0% | EventBus + Schema 提取 |
| OrderService | backend-dev-1 | 2 | 0 | 0% | |
| ApprovalService + 事件 | backend-dev-1 | 3 | 0 | 0% | |
| CustomerService | backend-dev-2 | 2 | 0 | 0% | |
| EventService | backend-dev-2 | 2 | 0 | 0% | |
| SupplierService | backend-dev-3 | 2 | 0 | 0% | |
| UserService | backend-dev-3 | 2 | 0 | 0% | |

---

## 3. 产出物清单

### Phase 3: 架构设计

| 产出物 | 文件路径 | 状态 |
|--------|----------|------|
| 重构方案 | `docs/refactoring-plan.md` | 已完成 |

### Phase 4: 并行开发

| 产出物 | 文件路径 | 状态 |
|--------|----------|------|
| 事件总线 | `app/events/__init__.py` | 未开始 |
| 事件类型 | `app/events/event_types.py` | 未开始 |
| 事件处理器 | `app/events/handlers.py` | 未开始 |
| Schema 提取 | `app/schemas/*.py` | 未开始 |
| OrderService | `app/services/order_service.py` | 未开始 |
| ApprovalService | `app/services/approval_service.py` | 未开始 |
| CustomerService | `app/services/customer_service.py` | 未开始 |
| EventService | `app/services/event_service.py` | 未开始 |
| SupplierService | `app/services/supplier_service.py` | 未开始 |
| UserService | `app/services/user_service.py` | 未开始 |
| 路由层精简 | `app/api/*.py`（6 个文件） | 未开始 |

---

## 4. 阻塞项与风险

| 编号 | 类型 | 描述 | 影响阶段 | 负责人 | 状态 |
|------|------|------|----------|--------|------|
| 1 | 风险 | 行为变更：重构可能无意改变业务行为 | Phase 4 | Team Lead | 已缓解：每模块重构后验证 API |
| 2 | 风险 | 事务边界：Service 层 commit 时点需与原路由一致 | Phase 4 | backend-dev-1 | 已缓解：保持相同事务边界 |

---

## 5. 下一步行动

1. 基础设施：创建 EventBus + 提取 Schema（前置依赖）
2. 并行启动 3 个后端工程师执行模块重构
3. 每模块完成后验证 API 行为不变
