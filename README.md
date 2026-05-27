# 婚庆管理系统 (Wedding Management System)

企业级婚庆行业管理平台，支持客户管理、订单管理、供应商管理、活动调度等核心功能。

## 系统架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│    MySQL    │
│  (Vue 3)    │     │   (FastAPI) │     │   (8.0)     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │
       │                   ▼
       │             ┌─────────────┐
       │             │    Redis    │
       │             │   (Cache)   │
       │             └─────────────┘
       │
       ▼
┌─────────────┐
│   Nginx     │
│  (Reverse   │
│   Proxy)    │
└─────────────┘
```

## 技术栈

### 前端
- **框架**: Vue 3 + TypeScript
- **状态管理**: Pinia
- **UI 组件**: Naive UI
- **构建工具**: Vite
- **HTTP 客户端**: Axios
- **路由**: Vue Router 4

### 后端
- **框架**: FastAPI (Python 3.13+)
- **ORM**: SQLAlchemy 2.0 (异步)
- **数据库**: MySQL 8.0
- **缓存**: Redis 7
- **认证**: JWT (HS256)
- **限流**: SlowAPI
- **文档**: OpenAPI/Swagger

### 基础设施
- **容器化**: Docker Compose
- **反向代理**: Nginx
- **监控**: Prometheus + Grafana
- **备份**: MySQL 自动备份脚本

## 核心功能

### 客户关系管理 (CRM)
- 客户信息管理（姓名、电话、性别、来源）
- 客户状态流转（潜在 → 跟进 → 意向 → 签约 → 流失）
- 跟进记录管理
- 客户回收站

### 订单管理
- 订单创建与状态流转（意向 → 已签 → 执行中 → 已完成/已取消）
- 订单明细（策划、场地、摄影、主持等）
- 付款记录管理
- 合同上传（PDF 文件校验）
- 折扣管理

### 供应商管理
- 供应商信息管理
- 供应商服务类型
- 供应商评价

### 活动调度
- 活动创建与状态管理
- 场地分配与冲突检测
- 员工排班管理
- 资源分配

### 系统管理
- 用户管理
- 角色权限管理（RBAC）
- 操作日志
- 通知管理

## 快速开始

### 环境要求
- Python 3.13+
- Node.js 20+
- MySQL 8.0
- Redis 7
- Docker & Docker Compose（可选）

### 本地开发

#### 1. 克隆代码
```bash
git clone https://github.com/tlbfpx/wedding.git
cd wedding
```

#### 2. 启动基础设施（Docker）
```bash
docker compose up -d mysql redis
```

#### 3. 后端设置
```bash
cd wedding-backend

# 创建虚拟环境
python3.13 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 环境变量
export DATABASE_URL="mysql+asyncmy://root:root@127.0.0.1:3306/wedding"
export REDIS_URL="redis://127.0.0.1:6379/0"
export JWT_SECRET="your-secret-key"

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 4. 前端设置
```bash
cd wedding-frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

#### 5. 访问应用
- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/api/docs

### Docker 部署

```bash
# 启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

## API 接口

### 认证接口
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/auth/login` | 用户登录 |
| POST | `/api/v1/auth/refresh` | 刷新 Token |
| POST | `/api/v1/auth/logout` | 用户登出 |
| GET | `/api/v1/auth/me` | 获取当前用户信息 |
| GET | `/api/v1/auth/csrf` | 获取 CSRF Token |

### 客户接口
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/customers` | 获取客户列表 |
| POST | `/api/v1/customers` | 创建客户 |
| GET | `/api/v1/customers/{id}` | 获取客户详情 |
| PUT | `/api/v1/customers/{id}` | 更新客户 |
| DELETE | `/api/v1/customers/{id}` | 删除客户 |

### 订单接口
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/orders` | 获取订单列表 |
| POST | `/api/v1/orders` | 创建订单 |
| GET | `/api/v1/orders/{id}` | 获取订单详情 |
| PUT | `/api/v1/orders/{id}` | 更新订单 |
| POST | `/api/v1/orders/{id}/contract` | 上传合同 |

### 健康检查
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/health` | 存活检查 |
| GET | `/api/v1/ready` | 就绪检查 |
| GET | `/metrics` | Prometheus 指标 |

## 安全特性

### 认证与授权
- JWT Token 认证
- Token 黑名单机制（登出后 Token 失效）
- 刷新令牌旋转（一次性使用）
- 账户锁定（5 次登录失败后锁定 30 分钟）

### CSRF 防护
- `X-CSRF-Token` 请求头验证
- 公开端点豁免（登录、刷新令牌等）

### 输入校验
- 文件类型魔数校验（防止类型欺骗攻击）
- 文件名路径遍历过滤
- SQL 注入防护（ORM 自动处理）

### 日志安全
- 敏感字段脱敏（password, token, api_key 等）

## 企业级特性

### 可观测性
- Prometheus 指标采集
- 结构化日志（JSON 格式）
- 请求 ID 追踪
- 健康检查端点（存活 + 就绪）

### 性能优化
- 数据库索引优化
- N+1 查询消除（joinedload）
- 连接池管理
- 文件分块写入

### DevOps
- Docker 容器化部署
- 非 root 用户运行
- 资源限制（CPU/内存）
- MySQL 自动备份
- 备份加密支持（GPG）

## 测试

### 后端测试
```bash
cd wedding-backend
source .venv/bin/activate
pytest tests/ -v
```

### 前端 E2E 测试
```bash
cd wedding-frontend
npm run test:e2e
```

### API 测试
```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

## 项目结构

```
wedding/
├── wedding-backend/
│   ├── app/
│   │   ├── api/              # API 路由
│   │   ├── models/          # 数据模型
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # 业务逻辑
│   │   ├── middleware/      # 中间件
│   │   ├── utils/           # 工具函数
│   │   └── events/          # 事件总线
│   ├── scripts/             # 脚本（备份等）
│   ├── tests/              # 测试
│   ├── Dockerfile
│   └── requirements.txt
├── wedding-frontend/
│   ├── src/
│   │   ├── api/             # API 调用
│   │   ├── stores/          # Pinia stores
│   │   ├── views/           # 页面组件
│   │   ├── router/          # 路由配置
│   │   └── App.vue
│   ├── e2e/                # E2E 测试
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

## 配置说明

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | MySQL 连接地址 | `mysql+asyncmy://root:root@mysql:3306/wedding` |
| `REDIS_URL` | Redis 连接地址 | `redis://redis:6379/0` |
| `JWT_SECRET` | JWT 密钥 | `production-secret-change-me` |
| `APP_ENV` | 运行环境 | `development` |
| `DEBUG` | 调试模式 | `false` |
| `CORS_ORIGINS` | CORS 允许的源 | `http://localhost:5173,http://localhost:3000` |

## License

MIT License