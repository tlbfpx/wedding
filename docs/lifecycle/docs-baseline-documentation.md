# 研发生命周期跟踪

> 分支名称：docs/baseline-documentation
> 需求规模：基线建档
> 迭代目标：对存量婚庆管理系统进行全面基线建档，建立文档体系
> 创建日期：2026-05-22
> 最后更新：2026-05-22

---

## 1. 阶段总览

| Phase | 阶段名称 | 状态 | 人工确认 | 开始时间 | 完成时间 | 备注 |
|-------|----------|------|----------|----------|----------|------|
| 0 | 基线建档 | 待确认 | 待确认 | 2026-05-22 | | |
| 1 | 需求分析与 PRD | 未开始 | | | | |
| 2 | 交互设计 | 未开始 | | | | |
| 3 | 架构设计 | 未开始 | | | | |
| 4 | 并行开发 | 未开始 | | | | |
| 5 | 集成测试 | 未开始 | | | | |

**状态说明**：未开始 → 进行中 → 待确认 → 已完成 / 跳过

---

## 2. 团队分配

### 角色分配

| 角色 | Agent 名称 | 状态 | 负责阶段 |
|------|-----------|------|----------|
| Team Lead | claude (主 agent) | 进行中 | 全流程协调 |
| 产品经理 | product-manager | 待启动 | Phase 0 |
| 后端开发工程师 1 | backend-dev-1 | 待启动 | Phase 0（模块：customers, orders, suppliers） |
| 后端开发工程师 2 | backend-dev-2 | 待启动 | Phase 0（模块：events, venues, users, approvals, auth） |
| 前端开发工程师 | frontend-dev | 待启动 | Phase 0 |
| 后端架构师 | architect | 待启动 | Phase 0（汇总） |

### Phase 4 模块开发进度

（基线建档阶段无需填写）

---

## 3. 产出物清单

### Phase 0: 基线建档

| 产出物 | 文件路径 | 状态 |
|--------|----------|------|
| 项目拓扑 | `docs/topology.md` | 已完成 |
| 现状 PRD | `docs/PRD.md` | 已完成 |
| 架构设计文档 | `docs/architecture.md` | 已完成 |
| 模块依赖关系 | `docs/module-dependencies.md` | 已完成 |
| 客户管理 - 接口契约 | `wedding-backend/docs/customers-contracts.md` | 已完成 |
| 客户管理 - 设计概览 | `wedding-backend/docs/customers-design-overview.md` | 已完成 |
| 排期管理 - 接口契约 | `wedding-backend/docs/events-contracts.md` | 已完成 |
| 排期管理 - 设计概览 | `wedding-backend/docs/events-design-overview.md` | 已完成 |
| 订单管理 - 接口契约 | `wedding-backend/docs/orders-contracts.md` | 已完成 |
| 订单管理 - 设计概览 | `wedding-backend/docs/orders-design-overview.md` | 已完成 |
| 供应商管理 - 接口契约 | `wedding-backend/docs/suppliers-contracts.md` | 已完成 |
| 供应商管理 - 设计概览 | `wedding-backend/docs/suppliers-design-overview.md` | 已完成 |
| 用户权限 - 接口契约 | `wedding-backend/docs/users-contracts.md` | 已完成 |
| 用户权限 - 设计概览 | `wedding-backend/docs/users-design-overview.md` | 已完成 |
| 审批管理 - 接口契约 | `wedding-backend/docs/approvals-contracts.md` | 已完成 |
| 审批管理 - 设计概览 | `wedding-backend/docs/approvals-design-overview.md` | 已完成 |
| 场地管理 - 接口契约 | `wedding-backend/docs/venues-contracts.md` | 已完成 |
| 场地管理 - 设计概览 | `wedding-backend/docs/venues-design-overview.md` | 已完成 |
| 认证模块 - 接口契约 | `wedding-backend/docs/auth-contracts.md` | 已完成 |
| 认证模块 - 设计概览 | `wedding-backend/docs/auth-design-overview.md` | 已完成 |
| 前端架构分析 | `wedding-frontend/docs/frontend-architecture.md` | 已完成 |

---

## 4. 阻塞项与风险

| 编号 | 类型 | 描述 | 影响阶段 | 负责人 | 状态 |
|------|------|------|----------|--------|------|
| | | | | | |

---

## 5. 下一步行动

1. 请求用户确认基线文档（Phase 0 人工确认网关）
2. 用户确认通过后，Phase 0 标记为"已完成"
