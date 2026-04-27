# 4C 医药企业分析系统

这是一个前后端分离的医药企业分析项目。

- 前端使用 Vue 3 + Vite，负责公司检索、行情展示、企业诊断、风险扫描和聊天入口。
- 后端使用 FastAPI + SQLAlchemy，当前已经完成运行时逻辑层重构。
- 智能体部分暂时保留为 LangChain 接入位，尚未接入正式提示词、工具编排和记忆链路。

## 当前项目结构

```text
4c/
├── frontend/                  # Vue3 + Vite 前端
├── backend/                   # FastAPI 后端
│   ├── main.py                # 应用入口
│   ├── app_bootstrap.py       # 启动期数据库探测与健康检查适配
│   ├── agent/                 # LangChain 占位层
│   ├── core/                  # 数据库模型、会话、仓储定义（冻结层）
│   ├── knowledge/             # 知识检索/同步层（冻结层）
│   ├── modules/               # 当前实际对外运行逻辑
│   │   ├── chat/              # 聊天接口与会话持久化
│   │   ├── stock/             # 公司、行情、自选股聚合接口
│   │   ├── analysis/          # 诊断、指标趋势、风险扫描
│   │   └── shared.py          # 运行时公共适配函数
│   ├── service/               # 原服务层（冻结层）
│   └── local_data/            # SQLite 本地库与导入数据
└── README.md
```

## 后端分层说明

当前后端按两层理解最准确。

第一层是冻结层：

- backend/core
- backend/service
- backend/knowledge

这三部分保留现有数据库模型、仓储和知识相关实现，本轮重构不直接修改它们。

第二层是运行时逻辑层：

- backend/main.py
- backend/app_bootstrap.py
- backend/modules
- backend/agent

这部分负责真实 HTTP 路由、聚合查询、诊断逻辑、错误处理和占位型智能体响应。

## 当前后端能力

### 1. 启动与数据库适配

- 应用启动入口在 backend/main.py。
- 启动时会执行 backend/app/bootstrap/runtime.py 中的初始化逻辑。
- 当前运行模式为 MySQL-only，不再自动回退到 SQLite。
- 后端启动前必须保证 .env 中配置的 MySQL 可连接，并且存在可用的 stock_agent 库。
- 健康检查会返回当前真实数据库连接状态；如果 MySQL 不可用，应用会在启动阶段直接失败，而不是自动降级。

### 2. 聊天接口

- 路由：POST /api/chat
- 当前返回 LangChain 占位响应，并会写入聊天会话与消息表。
- 返回体包含 session_id 和 agent_mode，其中 agent_mode 当前为 langchain-pending。

### 3. 股票与公司接口

- 路由前缀：/api/stock
- 已对齐当前数据库模型，提供公司聚合数据、行情、自选股和公司列表接口。
- 当本地数据库没有目标公司时，会返回 404，而不是 500。

### 4. 分析接口

- 路由前缀：/api/analysis
- 提供企业诊断、指标趋势、指标对比和风险扫描。
- 诊断逻辑当前基于财务热表、公告热表和新闻热表计算。

### 5. PDF 上传接口

- 路由：POST /api/upload_pdf
- 当前仍为占位接口。
- 带文件请求时会返回 501，明确说明尚未接入 PDF 入库和 LangChain 工作流。

## 已验证的运行结果

在当前工作区环境下，已经验证以下结果：

- backend/main.py 可以正常导入。
- app.router.chat、app.router.stock、app.router.analysis 等正式路由都可以正常导入。
- /health 可以返回 200。
- 当前环境下，/health 会显示 dialect 为 mysql，storage_mode 为 mysql-only。
- POST /api/chat 可以返回占位型智能体响应。
- GET /api/stock/companies 在空库场景下返回空数组。
- GET /api/analysis/risks 在空库场景下返回空结果。
- GET /api/stock/company?symbol=600276 在缺数据时返回 404。
- GET /api/analysis/diagnose?symbol=600276&year=2024 在缺数据时返回 404。

## 启动方式

### 后端

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
python main.py
```

注意：

- 必须先进入 backend 目录再执行 python main.py；如果在仓库根目录执行，会报找不到 main.py。
- 推荐直接使用 backend/.venv 中的解释器，避免混用系统 Python 或 Conda 环境。
- 首次启动前先基于 backend/.env.example 创建 backend/.env，再填入自己的 MySQL 连接信息。
- 当前后端依赖 MySQL；如果 127.0.0.1:3306 不可用，或 stock_agent 库不存在，服务不会启动。

默认地址：

```text
http://127.0.0.1:8000
```

### 前端

```powershell
cd frontend
npm install
npm run dev
```

注意：

- 如果终端提示 vite 不是内部或外部命令，说明 frontend 目录下还没有执行过 npm install。
- 前端默认直接请求 http://127.0.0.1:8000，因此要先确认后端已经在 8000 端口监听。

默认地址：

```text
http://127.0.0.1:5173
```

## 主要接口

- GET /health
- POST /api/chat
- GET /api/chat/history
- POST /api/upload_pdf
- GET /api/stock/companies
- GET /api/stock/company
- GET /api/stock/quote
- GET /api/stock/kline
- GET /api/stock/watchlist
- POST /api/stock/watchlist
- DELETE /api/stock/watchlist
- GET /api/analysis/diagnose
- GET /api/analysis/risks
- GET /api/analysis/compare
- GET /api/analysis/trend
- POST /api/openclaw/ingest  # OpenClaw 统一入库接口

## OpenClaw 数据入库对接

已完成 OpenClaw 后端统一入库对接，支持通过统一 JSON 格式导入各类数据：

- **接口地址**: `POST /api/openclaw/ingest`
- **支持数据类型**: 公司概况、财务报表、公告、新闻、医药事件、宏观指标、股票行情等 13 种数据类型
- **文档位置**:
  - 完整文档: `backend/OPENCLAW_INTEGRATION.md`
  - 快速开始: `backend/OPENCLAW_QUICK_START.md`
  - 实现总结: `backend/OPENCLAW_IMPLEMENTATION_SUMMARY.md`
- **测试脚本**: `backend/test_openclaw_integration.py`

快速测试：
```bash
cd backend
python test_openclaw_integration.py
```

## 当前限制

- 智能体仍是占位实现，还没有正式接入 LangChain 执行链。
- 如果 MySQL 中尚未导入公司数据，股票和分析接口会返回空结果或 404。
- 当前 README 仅描述现有运行状态，不再对应旧竞赛版的 repository/service/api 目录结构。