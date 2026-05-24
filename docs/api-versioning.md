# API 版本管理策略

> 日期：2026-05-24
> 状态：初稿

---

## 背景

当前 API 基路径为 `/api/v1/*`，随着业务迭代，接口契约会发生变化。为保证前端平稳升级和向后兼容，需要明确的版本管理策略。

---

## 版本策略

### 1. 版本标识

API 版本通过 URL 路径前缀标识：`/api/v{version}/{module}/{resource}`

- **当前版本**：v1（稳定）
- **未来版本**：v2（规划中）

### 2. 兼容性原则

| 变更类型 | 向后兼容 | 版本要求 |
|----------|----------|----------|
| 新增字段 | ✅ | 无需版本变更 |
| 新增可选参数 | ✅ | 无需版本变更 |
| 修改字段名 | ❌ | v2 新增，原字段标记废弃 |
| 删除字段 | ❌ | 先标记 `@deprecated`，经过弃用周期后删除 |
| 修改字段类型 | ❌ | v2 新增 |
| 修改业务逻辑 | ❌ | v2 新增 |
| 删除端点 | ❌ | 先标记 `@deprecated`，经过弃用周期后删除 |

### 3. 废弃（Deprecation）流程

当某个端点或字段需要废弃时：

1. **废弃标记**：在响应中添加 `X-Deprecated: true` header，并在响应 body 中添加 `deprecated_at` 时间戳
2. **文档更新**：在 OpenAPI 文档中标记为 `deprecated: true`
3. **通知前端**：通过站内通知或邮件告知前端团队
4. **弃用周期**：至少 **2 个版本迭代**（约 6 个月）后才可删除
5. **强制迁移**：在弃用周期结束后，前端必须迁移到新版本

### 4. 错误响应格式

v2 起统一错误响应格式：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "人类可读的错误信息",
    "detail": null,
    "request_id": "uuid",
    "version": "v2"
  }
}
```

### 5. 版本协商

#### 方案 A：URL 路径（当前采用）
```
GET /api/v1/customers
GET /api/v2/customers
```
优点：直观、易调试、易缓存
缺点：需要前端全部替换

#### 方案 B：Header 协商（备选）
```
GET /api/customers
Accept: application/vnd.wedding.v2+json
```
优点：URL 保持稳定
缺点：调试困难，易被 CDN 缓存策略忽略

**决策**：继续使用 URL 路径方案，与当前 v1 保持一致。

---

## v2 规划

### 计划在 v2 中引入的变更

| 变更 | 原因 |
|------|------|
| 分页格式统一为 cursor-based | 当前 offset-based 在大数据量时性能差 |
| 时间字段统一为 ISO 8601 | 当前混乱（有些用 timestamp，有些用 date） |
| 移除 `detail` 字段 | 简化为 `message` 即可 |
| `require_permission` 改为基于 resource 的权限 | 更细粒度控制 |

### v2 迁移计划

1. v2 上线后，v1 继续运行 **6 个月**
2. 期间前端逐步迁移到 v2
3. 6 个月后关闭 v1，前端必须全量切换

---

## 前端版本切换指南

1. 将 `wedding-frontend/src/api/index.ts` 中的 `baseURL` 从 `/api/v1` 改为 `/api/v2`
2. 更新对应的类型定义（DTO changes）
3. 运行 E2E 测试验证
4. 逐步灰度上线

---

## 参考

- [RFC 9110 HTTP Semantics - Versioning](https://www.rfc-editor.org/rfc/rfc9110.html#name.protocol-versioning)
- [Zalando REST Guidelines - Versioning](https://opensource.zalando.com/restful-api-guidelines/#evolution)