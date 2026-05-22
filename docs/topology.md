# 项目拓扑与路径映射

> 拓扑类型：多服务
> 最后更新：2026-05-22

---

## 路径映射表

| 服务标识 | 服务名称 | 服务根路径 | 模块路径模式 | 服务文档路径 | 说明 |
|----------|----------|-----------|-------------|-------------|------|
| backend | 后端 API 服务 | `wedding-backend/` | `wedding-backend/app/<module>/` | `wedding-backend/docs/` | FastAPI + SQLAlchemy async |
| frontend | 前端 Web 应用 | `wedding-frontend/` | `wedding-frontend/src/views/<module>/` | `wedding-frontend/docs/` | Vue 3 + Naive UI + TS |

---

## 路径解析规则

1. **全局文档**（`docs/PRD.md`、`docs/topology.md`、`docs/architecture.md` 等）始终在项目根 `docs/` 下
2. **后端模块文档**：`wedding-backend/<module>/docs/`（如 `wedding-backend/app/api/docs/`）
3. **前端页面**：`wedding-frontend/src/views/<module>/`，对应路由在 `src/router/index.ts`
4. **后端 API 模块**：`wedding-backend/app/api/<module>.py`
5. **后端数据模型**：`wedding-backend/app/models/<module>.py`
6. **后端中间件**：`wedding-backend/app/middleware/`
7. **前端 API 层**：`wedding-frontend/src/api/<module>.ts`
8. **跨服务依赖**：前端通过 axios 调用后端 REST API（`/api/v1/*`），服务间通过 HTTP 通信

## 服务通信方式

- 前端 → 后端：REST API（`/api/v1/*`），JWT Bearer 认证
- 后端数据库：MySQL 8，asyncmy 驱动，SQLAlchemy 2.0 async ORM
- 前端构建：Vite + Vue 3 + TypeScript
