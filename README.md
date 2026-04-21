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
- 启动时会执行 backend/app_bootstrap.py 中的初始化逻辑。
- 运行时优先尝试连接配置中的 MySQL。
- 如果当前 MySQL 实际暴露的是旧竞赛表结构，而不是当前代码依赖的新热表结构，系统会自动切换到本地 SQLite。
- SQLite 默认路径为 backend/local_data/stock_agent.db。
- 切换到 SQLite 后，系统会自动按当前模型建表，并创建演示用户。

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
- modules.chat.service、modules.stock.service、modules.analysis.service 都可以正常导入。
- /health 可以返回 200。
- 当检测到当前 MySQL 是旧结构时，/health 会显示 dialect 为 sqlite，storage_mode 为 sqlite-fallback。
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
python main.py
```

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

## 当前限制

- 智能体仍是占位实现，还没有正式接入 LangChain 执行链。
- 如果 SQLite 本地库尚未导入公司数据，股票和分析接口会返回空结果或 404。
- 当前 README 仅描述现有运行状态，不再对应旧竞赛版的 repository/service/api 目录结构。