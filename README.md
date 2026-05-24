# 4C 医药企业智能分析系统

前后端分离的医药企业投研分析平台，集成 AI 对话、财务分析、风险预警、行业对比等功能。

## 运行方法
点击：启动.vbs,等待程序安装环境，自行启动，如果环境安装完毕后没有反应，关闭cmd窗口再运行一次，启动成功后，找到前端页面运行的cmd窗口，点击上面绿色链接即可进入。


## 技术栈

- 前端：Vue 3 + Vite + ECharts + Pinia
- 后端：FastAPI + SQLAlchemy + MySQL
- AI：Kimi (Moonshot) 大模型，支持多模式分析和工具自主调用
- 向量检索：ChromaDB + BGE-small-zh 嵌入模型

## 项目结构

```text
4c/
├── start.bat                  # 一键启动脚本（自动建环境、装依赖、启服务）
├── .env                       # 配置文件（MySQL、Kimi API 等）
├── check_db.py                # 数据库连通性检查
├── frontend/                  # Vue 3 前端
│   └── src/
│       ├── views/             # 页面组件
│       ├── components/        # 通用组件
│       ├── api/               # 后端接口封装
│       ├── store/             # Pinia 状态管理
│       └── router/            # 路由配置
├── backend/                   # FastAPI 后端
│   ├── main.py                # 应用入口
│   ├── config.py              # 配置加载（读取根目录 .env）
│   ├── requirements.txt       # Python 依赖
│   ├── agent/                 # AI 智能体模块
│   │   ├── dialogue_agent.py  # 对话主控（多模式分析 + 工具流程）
│   │   ├── butterfly_analyzer.py  # 蝴蝶效应分析器
│   │   ├── integration/       # 智能体集成层
│   │   │   ├── langgraph_agent.py   # LangGraph 工具自主调用
│   │   │   ├── react_agent.py       # ReAct 推理链
│   │   │   ├── tool_planner.py      # 预定义工具计划
│   │   │   ├── tool_executor.py     # 工具执行器
│   │   │   ├── mode_resolver.py     # 分析模式识别
│   │   │   └── entity_resolver.py   # 实体解析（公司/药品）
│   │   ├── llm_clients/       # LLM 客户端
│   │   │   ├── kimi_client.py # Kimi API 封装（流式 + 重试）
│   │   │   └── glm_client.py  # GLM API 封装
│   │   ├── tools/             # 工具函数（财务、公告、新闻等）
│   │   └── prompts/           # 提示词模板
│   ├── app/                   # Web 应用层
│   │   ├── router/            # API 路由（20+ 模块）
│   │   ├── core/              # 数据库模型与会话
│   │   ├── service/           # 业务服务层
│   │   ├── knowledge/         # 知识检索（向量 + 结构化）
│   │   └── bootstrap/         # 启动初始化
│   ├── crawler/               # 数据爬取与转换
│   ├── ingest_center/         # 数据入库中心
│   └── scripts/               # 运维脚本（向量库重建、数据导入等）
└── docs/                      # 项目文档
```

## 快速启动

### 前置要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0+（启动时会自动创建 `stock_agent` 数据库）

### 一键启动

双击 `start.bat`，脚本会自动完成：

1. 检查 Python 和 Node.js 环境
2. 创建虚拟环境并安装后端依赖
3. 安装前端依赖
4. 检查 .env 配置
5. 启动后端（端口 8001）和前端（端口 5173）

### 手动启动

后端：

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

### 配置说明

项目根目录 `.env` 文件：

```ini
# 应用
APP_PORT=8001
ALLOW_ORIGINS=http://127.0.0.1:5173,http://localhost:5173

# MySQL
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的密码
MYSQL_DATABASE=stock_agent

# Kimi (Moonshot) AI
KIMI_API_KEY=你的API密钥
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODEL=kimi-k2.5
```

## AI 分析模式

系统支持 11 种分析模式，通过前端选择或自动识别触发：

| 模式 | 说明 |
|------|------|
| 普通模式 | 预定义工具流程（公司信息→财务→公告→新闻），结构化数据驱动回答 |
| 企业分析 | 综合评估企业经营状况 |
| 财务分析 | 深度解读财报数据 |
| 管线分析 | 药品研发管线与临床进展 |
| 政策/集采 | 政策影响与集采事件分析 |
| 风险预警 | 识别经营与合规风险 |
| 行业对比 | 多公司多指标可视化对比 |
| 图表分析 | 数据可视化解读 |
| 生成报告 | 结构化研究报告输出 |
| 归因分析 | 业绩变动归因 |
| 蝴蝶效应 | 事件传导链路推演 |

支持工具自主调用模式（LangGraph），AI 自行决定调用哪些工具、调用几次。

## API 概览

后端提供 RESTful API，主要模块：

- `/api/chat` — AI 对话（SSE 流式）
- `/api/agent` — 智能体调用
- `/api/query` — 快速查询
- `/api/company` — 公司信息
- `/api/financial` — 财务数据
- `/api/stock` — 行情与自选股
- `/api/analysis` — 诊断与分析
- `/api/announcement` — 公告检索
- `/api/news` — 新闻检索
- `/api/retrieval` — 向量检索
- `/api/butterfly` — 蝴蝶效应
- `/api/openclaw` — 统一数据入库
- `/api/ingest` — 数据导入
- `/api/maintenance` — 系统维护
- `/health` — 健康检查

完整 API 文档：启动后访问 `http://localhost:8001/docs`

## 默认访问地址

- 前端：http://localhost:5173
- 后端：http://localhost:8001
- API 文档：http://localhost:8001/docs
