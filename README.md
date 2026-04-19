# 股票智能咨询智能体（MySQL 版竞赛项目）

这是一个可直接启动的前后端分离项目骨架，适合课程设计、比赛演示和快速原型开发。

## 技术栈
- 前端：Vue3 + Vite + Pinia + Vue Router + Axios + ECharts
- 后端：FastAPI + SQLAlchemy + PyMySQL
- 数据库：MySQL 8.0
- 数据源：AKShare（实时行情）

## 项目结构
```text
stock-agent-web/
├── frontend/   # Vue3 前端
├── backend/    # FastAPI 后端
└── README.md
```

## 一、后端目录（MySQL 版）
```text
backend/
├── main.py
├── config.py
├── .env.example
├── requirements.txt
├── api/
│   ├── chat.py
│   └── stock.py
├── agent/
│   ├── agent.py
│   ├── prompt.py
│   └── tools.py
├── data/
│   └── akshare_client.py
├── database/
│   ├── base.py
│   ├── session.py
│   └── init_db.py
├── models/
│   ├── user.py
│   ├── chat_history.py
│   ├── stock_daily.py
│   └── watchlist.py
├── repository/
│   ├── user_repo.py
│   ├── chat_repo.py
│   ├── stock_repo.py
│   └── watchlist_repo.py
├── schemas/
│   ├── chat.py
│   └── stock.py
├── service/
│   ├── chat_service.py
│   └── stock_service.py
└── utils/
    └── logger.py
```

## 二、MySQL 数据表
项目启动时会自动建表并写入演示用户与默认自选股。

- `users`：用户表
- `chat_history`：聊天记录表
- `watchlist`：自选股表
- `stock_daily`：股票历史日线缓存表

## 三、启动前准备
建议先确认本机已安装以下环境：

- Python 3.10 及以上
- Node.js 18 及以上
- MySQL 8.0

先在 MySQL 中创建数据库：

```sql
CREATE DATABASE stock_agent CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
```

然后把 `backend/.env.example` 复制为 `backend/.env`，按你的 MySQL 账号修改：

```bash
cd backend
# Windows PowerShell
Copy-Item .env.example .env

# macOS / Linux
# cp .env.example .env
```

`backend/.env` 示例：

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DATABASE=stock_agent
DEMO_USER_ID=1
DEMO_USERNAME=demo_user
ANTHROPIC_API_KEY=your_api_key
ANTHROPIC_BASE_URL=https://api.anthropic.com
CLAUDE_MODEL=claude-sonnet-4-6
```

说明：

- 后端启动时会自动建表，并初始化演示用户和默认自选股。
- `ANTHROPIC_API_KEY` 不影响服务启动，但如果不配置，聊天接口会返回 AI 服务调用失败提示。
- `.env` 文件按相对路径加载，因此后端命令请在 `backend` 目录下执行。

## 四、启动后端
推荐在项目根目录打开两个终端：一个运行后端，一个运行前端。

### 方式 A：conda 环境
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### 方式 B：venv 环境
```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Windows CMD:
# .venv\Scripts\activate.bat

# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

如果 PowerShell 提示脚本执行被禁止，可先执行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

后端启动成功后，默认会监听：

```text
http://127.0.0.1:8000
```

接口示例：
- `GET /health`
- `POST /api/chat`
- `GET /api/stock/quote?symbol=600519`
- `GET /api/stock/kline?symbol=600519&days=30`
- `GET /api/stock/watchlist?user_id=1`

## 五、启动前端
先把 `frontend/.env.example` 复制为 `frontend/.env`：

```bash
cd frontend
# Windows PowerShell
Copy-Item .env.example .env

# macOS / Linux
# cp .env.example .env
```

`frontend/.env` 示例：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_DEMO_USER_ID=1
```

再安装依赖并启动开发服务器：

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：
```text
http://127.0.0.1:5173
```

启动后，浏览器打开前端地址即可访问系统。

## 六、推荐启动顺序
1. 启动 MySQL，并确认已创建 `stock_agent` 数据库。
2. 在 `backend` 目录下配置 `.env`，安装依赖后执行 `python main.py`。
3. 访问 `http://127.0.0.1:8000/health`，确认后端健康检查通过。
4. 在 `frontend` 目录下配置 `.env`，安装依赖后执行 `npm run dev`。
5. 打开 `http://127.0.0.1:5173` 进行页面访问和联调。

## 七、系统运行逻辑
1. 前端把聊天请求发送给 FastAPI。
2. 后端智能体调用 AKShare 获取实时行情。
3. 问答结果写入 `chat_history`。
4. 自选股从 `watchlist` 表读取。
5. 股票历史日线优先查 `stock_daily`，不足时再从 AKShare 拉取并写回 MySQL。

## 八、示例提问
- 帮我分析贵州茅台
- 看一下 600519
- 平安银行今天怎么样
- 查看 000001 最近走势

## 九、说明
1. 这是竞赛版结构，重点是演示完整链路，而不是完整金融终端。
2. MySQL 主要用于持久化用户、自选股和聊天记录，同时缓存历史日线数据。
3. AKShare 负责实时股票行情；如果接口异常，系统会回退到内置演示数据。
