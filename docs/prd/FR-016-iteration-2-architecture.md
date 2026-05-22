# 迭代 2 架构设计

> 日期：2026-05-22
> 分支：feat/iteration-2-report-notification-import
> 范围：FR-013 数据报表导出、FR-014 消息通知、FR-015 数据导入

---

## 1. 技术方案

### 1.1 新增依赖

| 库 | 用途 | 版本 |
|----|------|------|
| openpyxl | Excel 读写（报表导出 + 数据导入） | >=3.1.0 |

仅需新增 openpyxl 一个依赖。CSV 导入使用 Python 内置 `csv` 模块。

### 1.2 通知模型设计

新增 `Notification` 模型，位于 `app/models/notification.py`：

```python
class NotificationType(str, Enum):
    approval = "approval"
    schedule = "schedule"
    follow_up = "follow_up"
    system = "system"

class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(20))
    is_read: Mapped[bool] = mapped_column(default=False, index=True)
    related_id: Mapped[Optional[int]] = mapped_column(default=None)
    related_type: Mapped[Optional[str]] = mapped_column(String(20), default=None)
```

索引策略：`(user_id, is_read)` 复合索引支撑未读计数查询。

### 1.3 领域事件扩展

在现有 EventBus 机制上新增事件类型，用于触发通知：

| 事件类型 | 触发时机 | 通知对象 |
|----------|----------|----------|
| `approval.created` | 创建审批 | 审批人（管理员/主管） |
| `approval.resolved` | 审批决定 | 审批申请人 |
| `event.created` | 创建排期 | 关联订单的销售 |
| `event.updated` | 修改排期 | 关联订单的销售 + 策划师 |

通知处理器在 `app/events/handlers.py` 中注册，与现有审批事件处理器并列。

### 1.4 报表导出架构

```
ReportService(db: AsyncSession)
├── export_orders(date_start, date_end, status, sale_id) → StreamingResponse
├── export_customers(date_start, date_end, status, sale_id) → StreamingResponse
└── export_finance(date_start, date_end, sale_id) → StreamingResponse
```

使用 openpyxl 的 `Workbook` 在内存中构建 Excel，通过 `StreamingResponse` 返回文件流。枚举值映射为中文的映射表定义在 Service 内部。

### 1.5 数据导入架构

```
ImportService(db: AsyncSession)
├── get_template(import_type) → StreamingResponse  # 下载模板
├── validate_file(file) → None  # 校验文件格式和大小
├── import_customers(file) → ImportResult
└── import_suppliers(file) → ImportResult
```

流程：
1. 校验文件格式（xlsx/csv）和大小（≤5MB）
2. 读取表头，校验必填列
3. 逐行校验数据（手机号格式/唯一性、枚举值匹配）
4. 批量插入有效行，收集错误行
5. 返回 `ImportResult(total, success, failed, errors)`

---

## 2. API 设计

### 2.1 报表导出

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/reports/export` | 导出报表，参数：report_type, date_start, date_end, status, sale_id |

### 2.2 消息通知

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/notifications` | 通知列表（分页、类型筛选、已读筛选） |
| GET | `/api/v1/notifications/unread-count` | 未读计数 |
| PUT | `/api/v1/notifications/read` | 批量标记已读（body: {ids: [1,2,3]}） |
| PUT | `/api/v1/notifications/read-all` | 全部标记已读 |

### 2.3 数据导入

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/imports/template` | 下载导入模板，参数：import_type |
| POST | `/api/v1/imports/upload` | 上传文件导入，参数：import_type, file |

---

## 3. 新增/变更文件清单

### 后端新增

| 文件 | 说明 |
|------|------|
| `app/models/notification.py` | Notification 模型 |
| `app/services/report_service.py` | 报表导出 Service |
| `app/services/import_service.py` | 数据导入 Service |
| `app/services/notification_service.py` | 通知 Service |
| `app/api/reports.py` | 报表路由 |
| `app/api/notifications.py` | 通知路由 |
| `app/api/imports.py` | 导入路由 |
| `app/schemas/notification.py` | 通知 Schema |
| `app/schemas/report.py` | 报表 Schema |
| `app/schemas/import_schema.py` | 导入 Schema |
| `migrations/versions/xxx_add_notifications.py` | 通知表迁移 |

### 后端变更

| 文件 | 变更 |
|------|------|
| `app/models/__init__.py` | 新增 Notification 导入 |
| `app/events/event_types.py` | 新增事件类型常量 |
| `app/events/handlers.py` | 新增通知相关事件处理器 |
| `app/main.py` | 注册新路由 |
| `requirements.txt` | 新增 openpyxl |

### 前端新增/变更

| 文件 | 说明 |
|------|------|
| `src/api/notifications.ts` | 通知 API |
| `src/api/reports.ts` | 报表导出 API |
| `src/api/imports.ts` | 数据导入 API |
| `src/views/Notifications.vue` | 通知列表页 |
| `src/components/NotificationBell.vue` | 导航栏通知气泡组件 |
| `src/layouts/MainLayout.vue` | 集成 NotificationBell + 轮询 |
| 各列表页 | 新增"导出"按钮 |
| 各列表页 | 新增"导入"按钮（客户/供应商） |

---

## 4. 开发任务分解

### 模块 A：报表导出 + 数据导入（backend-dev-1）

1. 安装 openpyxl，更新 requirements.txt
2. 创建 Alembic 迁移：通知表（为模块 B 前置准备）
3. 实现 ReportService（3 个导出方法 + 枚举中文映射）
4. 实现 ImportService（模板下载 + 客户导入 + 供应商导入）
5. 创建报表和导入路由
6. 注册路由到 main.py

### 模块 B：消息通知（backend-dev-2）

1. 创建 Notification 模型（依赖模块 A 的迁移）
2. 实现 NotificationService（CRUD + 未读计数 + 批量已读）
3. 扩展事件类型（approval.created, approval.resolved, event.created, event.updated）
4. 实现通知事件处理器
5. 创建通知路由
6. 注册路由到 main.py

### 模块 C：前端集成（frontend-dev）

1. 创建通知 API + NotificationBell 组件 + MainLayout 轮询集成
2. 创建通知列表页 + 路由注册
3. 客户/订单/供应商列表页添加"导出"按钮
4. 客户/供应商列表页添加"导入"按钮 + 导入弹窗

---

## 5. 依赖关系

```
模块 A 任务 1 (openpyxl) ───┐
模块 A 任务 2 (迁移)  ──────┼── 模块 B 任务 1 (依赖迁移)
                            │
模块 A 任务 3-6 (报表+导入) │
                            │
模块 C (前端) ──────────────┴── 依赖模块 A、B 的 API 就绪
```

模块 A 和模块 B 可并行开发（模块 B 使用模块 A 创建的迁移文件，但模型定义可提前）。
