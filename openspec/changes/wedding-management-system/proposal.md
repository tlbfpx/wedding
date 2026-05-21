## Why

大型婚庆公司（20+ 人）目前缺乏统一的内部管理系统，客户信息分散、排期靠人工协调、订单财务流程不规范、供应商管理混乱。需要一套覆盖核心业务流程的管理系统，提升协作效率、减少错漏、支撑管理层数据化决策。

## What Changes

- 新增客户管理（CRM）模块：客户信息管理、跟进记录、公海池回收与认领机制
- 新增排期与资源管理模块：日历视图排期、场地管理、人员排班、冲突检测
- 新增订单与财务模块：订单全生命周期管理、收款登记、合同上传、报价单 PDF 导出、审批流程
- 新增供应商管理模块：供应商信息与服务报价管理、订单完成后评价、满意度排名
- 新增数据看板：营业额、订单量、客户转化漏斗、销售排行、收款统计、排期热力图
- 新增系统管理：员工与角色权限管理（RBAC）、操作日志

## Capabilities

### New Capabilities

- `auth`: JWT 认证与授权，登录/登出/Token 刷新，登录失败锁定，权限中间件
- `customer-management`: 客户信息 CRUD、跟进记录、公海池（自动回收 + 认领）、客户转移、客户来源管理
- `schedule-management`: 活动/婚礼排期、日历视图、场地管理、人员排班、资源分配、冲突检测
- `order-management`: 订单 CRUD、订单明细、状态流转（意向→签约→执行→完成/取消）、收款登记、合同上传、报价单 PDF 导出
- `approval-workflow`: 折扣/退款/取消审批流程，单级审批，审批通过自动执行
- `supplier-management`: 供应商信息 CRUD、服务报价管理、供应商评价与评分
- `dashboard`: 数据看板（营业额/订单量/转化漏斗/销售排行/收款统计/排期热力图/供应商满意度）
- `system-management`: 员工管理、角色与权限（RBAC，模块级+数据级+操作级）、操作日志
- `file-upload`: 文件上传与存储（合同 PDF/图片），本地文件系统存储

### Modified Capabilities

（无现有能力需要修改）

## Impact

- **新建两个工程**：wedding-backend（FastAPI Python）和 wedding-frontend（Vue 3 TypeScript）
- **基础设施依赖**：MySQL 8、Redis
- **部署方式**：Docker Compose（4 容器：frontend/nginx、backend/uvicorn、mysql、redis）
- **外部依赖**：无第三方 SaaS 集成，纯自部署
- **数据量预估**：客户数千级、订单千级、排期百级/月，MySQL 完全可承载
