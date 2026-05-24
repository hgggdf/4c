# Step 3: 修正分层架构 — Codex 执行指令

## 总体目标

将 `app/router/analysis_service.py` 和 `app/router/stock_service.py` 中的业务逻辑迁移到 `app/service/` 层，消除 agent 层对 router 层的反向依赖。

**核心原则：功能完全不变。** 所有 API 端点的输入输出、行为、错误处理必须与迁移前一模一样。

---

## 执行规则

- 每完成一个子步骤，返回：✅ 修改摘要、📝 关键代码片段、❓ 需确认的问题
- **不要修改任何业务逻辑**——只是移动代码位置和调整 import 路径
- 如果发现某个方法的依赖关系无法简单迁移（如循环依赖），**停下来报告**
- 每步完成后跑验证

---

### Step 3.1 — 迁移 AnalysisService 到 service 层

**当前状态：**
- `backend/app/router/analysis_service.py`（~580 行）包含所有分析业务逻辑
- 被以下文件引用：
  - `app/router/analysis.py:7` — 路由层
  - `agent/integration/glm_agent.py:64` — agent 层（反向依赖）
  - `agent/dialogue_agent.py:952, 1153` — agent 层（反向依赖）

**具体操作：**

1. **重命名文件**（不是新建，是直接移动）：
   ```bash
   mv backend/app/router/analysis_service.py backend/app/service/analysis_service.py
   ```

2. **修改被移动文件内的相对 import**：

   `backend/app/service/analysis_service.py` 中有：
   ```python
   from .shared import normalize_percent, resolve_company, to_float
   ```
   
   这是原来 `app/router/shared.py` 的相对引用。迁移后需要改为绝对路径：
   ```python
   from app.router.shared import normalize_percent, resolve_company, to_float
   ```

   同理检查文件内所有 `from .xxx` 的相对引用，全部改为 `from app.router.xxx` 或 `from app.service.xxx`（取决于目标模块位置）。

3. **在原位置创建转发模块**（兼容性，避免外部引用断裂）：

   创建 `backend/app/router/analysis_service.py`（新文件，只做 re-export）：
   ```python
   """向后兼容入口 — 实际逻辑已迁移到 app.service.analysis_service。"""
   from app.service.analysis_service import AnalysisService, DiagnoseResult, DimensionResult

   __all__ = ["AnalysisService", "DiagnoseResult", "DimensionResult"]
   ```

4. **更新所有引用方的 import 路径**（优先改为直接引用 service 层）：

   **`backend/app/router/analysis.py:7`**
   ```python
   # 修改前：
   from app.router.analysis_service import AnalysisService
   # 修改后：
   from app.service.analysis_service import AnalysisService
   ```

   **`backend/agent/integration/glm_agent.py:64`**（函数内局部 import）
   ```python
   # 修改前：
   from app.router.analysis_service import AnalysisService
   # 修改后：
   from app.service.analysis_service import AnalysisService
   ```

   **`backend/agent/dialogue_agent.py:952, 1153`**（函数内局部 import）
   ```python
   # 修改前：
   from app.router.analysis_service import AnalysisService
   # 修改后：
   from app.service.analysis_service import AnalysisService
   ```

5. **检查被移动文件的其他依赖**：
   ```bash
   grep -n "^from \.\|^import \." backend/app/service/analysis_service.py
   ```
   确保所有相对 import 都已正确调整。如果有 `from .schemas.analysis import ...`，需改为 `from app.router.schemas.analysis import ...`。

**验证标准：**
```bash
python -c "from app.service.analysis_service import AnalysisService; print('OK')"
python -c "from app.router.analysis_service import AnalysisService; print('OK')"  # 兼容层
python -c "from app.router.analysis import router; print('OK')"
python -c "from agent.integration.glm_agent import GLMMinimalAgent; print('OK')"
python -c "from agent.dialogue_agent import DialogueAgent; print('OK')"
python -c "from main import app; print('OK')"
```

---

### Step 3.2 — 迁移 StockService 到 service 层

**当前状态：**
- `backend/app/router/stock_service.py`（~492 行）包含所有股票业务逻辑
- 被以下文件引用：
  - `app/router/stock.py:8` — 路由层

**具体操作：**

1. **重命名文件**：
   ```bash
   mv backend/app/router/stock_service.py backend/app/service/stock_service.py
   ```

2. **修改被移动文件内的相对 import**：

   `backend/app/service/stock_service.py` 中有：
   ```python
   from .shared import build_quote_payload, ensure_demo_user, get_latest_trade_rows, normalize_percent, resolve_company, serialize_kline_row, to_float
   ```
   
   改为：
   ```python
   from app.router.shared import build_quote_payload, ensure_demo_user, get_latest_trade_rows, normalize_percent, resolve_company, serialize_kline_row, to_float
   ```

3. **在原位置创建转发模块**：

   创建 `backend/app/router/stock_service.py`（新文件，只做 re-export）：
   ```python
   """向后兼容入口 — 实际逻辑已迁移到 app.service.stock_service。"""
   from app.service.stock_service import StockService

   __all__ = ["StockService"]
   ```

4. **更新引用方**：

   **`backend/app/router/stock.py:8`**
   ```python
   # 修改前：
   from app.router.stock_service import StockService
   # 修改后：
   from app.service.stock_service import StockService
   ```

5. **搜索其他可能的引用**：
   ```bash
   grep -rn "from app.router.stock_service\|from .stock_service\|import stock_service" backend/ --include="*.py" | grep -v __pycache__ | grep -v ".venv"
   ```
   如果有其他引用 → 同样更新。

**验证标准：**
```bash
python -c "from app.service.stock_service import StockService; print('OK')"
python -c "from app.router.stock_service import StockService; print('OK')"  # 兼容层
python -c "from app.router.stock import router; print('OK')"
python -c "from main import app; print('OK')"
```

---

### Step 3.3 — 迁移 router 层的 ChatService 到 service 层

**当前状态：**
- `backend/app/router/chat_service.py`（~258 行）包含对话生成逻辑（`handle_chat`, `get_chat_history`）
- `backend/app/service/chat_service.py`（~143 行）处理 session CRUD
- 这两个是**不同的服务**，不要合并！它们职责不同。

**具体操作：**

1. 将 `app/router/chat_service.py` 重命名为 `app/service/chat_dialogue_service.py`（取一个不冲突的名字）：
   ```bash
   mv backend/app/router/chat_service.py backend/app/service/chat_dialogue_service.py
   ```

2. **修改被移动文件内的相对 import**：

   检查文件中所有 `from .shared import ...` 或 `from .schemas.xxx import ...` 的引用，改为绝对路径：
   ```python
   # 修改前：
   from .shared import build_quote_payload, ensure_demo_user, get_latest_trade_rows, resolve_company
   # 修改后：
   from app.router.shared import build_quote_payload, ensure_demo_user, get_latest_trade_rows, resolve_company

   # 修改前（如果有）：
   from .schemas.chat import ChatHistoryRecord, ChatRequest, ChatResponse
   # 修改后：
   from app.router.schemas.chat import ChatHistoryRecord, ChatRequest, ChatResponse
   ```

3. **在原位置创建转发模块**：

   创建 `backend/app/router/chat_service.py`（新文件，只做 re-export）：
   ```python
   """向后兼容入口 — 实际逻辑已迁移到 app.service.chat_dialogue_service。"""
   from app.service.chat_dialogue_service import ChatService

   __all__ = ["ChatService"]
   ```

4. **更新引用方**：

   **`backend/app/router/chat.py:14`**
   ```python
   # 修改前：
   from app.router.chat_service import ChatService as RuntimeChatService
   # 修改后：
   from app.service.chat_dialogue_service import ChatService as RuntimeChatService
   ```

5. **搜索其他引用**：
   ```bash
   grep -rn "from app.router.chat_service\|from .chat_service" backend/ --include="*.py" | grep -v __pycache__ | grep -v ".venv"
   ```

**验证标准：**
```bash
python -c "from app.service.chat_dialogue_service import ChatService; print('OK')"
python -c "from app.router.chat_service import ChatService; print('OK')"  # 兼容层
python -c "from app.router.chat import router; print('OK')"
python -c "from main import app; print('OK')"
```

---

### Step 3.4 — 将 `app/router/shared.py` 中的通用工具下沉

**背景：**

迁移后，`app/service/analysis_service.py`、`app/service/stock_service.py`、`app/service/chat_dialogue_service.py` 都需要 import `app/router/shared.py` 中的工具函数。这形成了 service → router 的反向依赖。

**具体操作：**

1. **检查 `app/router/shared.py` 的内容**：
   ```bash
   grep -n "^def \|^class " backend/app/router/shared.py
   ```

2. **将纯工具函数（不依赖 FastAPI/Request 的）迁移到 `app/core/utils/` 或 `app/service/` 下的某个共享位置。**

   可能的目标：
   - `resolve_company()` → `app/core/utils/company.py`
   - `to_float()` → 已在 `app/core/utils/convert.py`（Step 2 已做）
   - `normalize_percent()` → `app/core/utils/convert.py`
   - `build_quote_payload()` → `app/service/helpers.py`（或留在 shared.py）
   - `ensure_demo_user()` → `app/service/helpers.py`
   - `get_latest_trade_rows()` → `app/service/helpers.py`
   - `serialize_kline_row()` → `app/service/helpers.py`

3. **方案选择**：

   > ⚠️ 如果 `shared.py` 中的函数较多（>10 个）且彼此耦合，这一步可能过于复杂。
   > 
   > **安全选项**：暂时保留 `app/router/shared.py` 在原位，让 service 层通过绝对路径 `from app.router.shared import ...` 引用它。虽然从架构上不完美（service 依赖 router 的工具文件），但**功能完全不变**，可以在后续 Step 4 拆分巨型文件时再处理。

   **Codex 判断规则**：
   - 如果 `shared.py` 中的函数**都不依赖 FastAPI、Request、Response 等 HTTP 概念** → 整体移动到 `app/service/shared.py`
   - 如果部分函数依赖 HTTP 概念 → 只移动不依赖 HTTP 的部分，其余留在 router 层
   - 如果移动会导致超过 5 个文件连锁修改 → **停下来报告**，暂时保留现状

**验证标准：**
```bash
python -c "from main import app; print('OK')"
# 所有现有的 API 端点仍可正常访问
```

---

## 总验证

完成以上所有子步骤后：

```bash
cd backend

# 启动检查
python -c "from main import app; print('Backend OK')"

# 核心模块导入
python -c "from app.service.analysis_service import AnalysisService; print('OK')"
python -c "from app.service.stock_service import StockService; print('OK')"
python -c "from app.service.chat_dialogue_service import ChatService; print('OK')"
python -c "from agent.integration.glm_agent import GLMMinimalAgent; print('OK')"
python -c "from agent.dialogue_agent import DialogueAgent; print('OK')"

# 兼容层仍可用
python -c "from app.router.analysis_service import AnalysisService; print('OK')"
python -c "from app.router.stock_service import StockService; print('OK')"
python -c "from app.router.chat_service import ChatService; print('OK')"

# agent 层不再 import router 层（除了 shared.py 临时保留）
grep -rn "from app.router" backend/agent/ --include="*.py" | grep -v __pycache__ | grep -v ".venv"
# 预期：空（如果 Step 3.4 完成了 shared.py 迁移）
# 或只有 from app.router.shared（如果 Step 3.4 选择保留）

# 前端构建
cd ../frontend && npx vite build
```

---

## 架构变化对比

**迁移前：**
```
app/router/analysis_service.py  ← agent/integration/glm_agent.py (反向依赖！)
app/router/stock_service.py     ← app/router/stock.py
app/router/chat_service.py      ← app/router/chat.py
```

**迁移后：**
```
app/service/analysis_service.py      ← agent/integration/glm_agent.py (正向依赖 ✅)
app/service/stock_service.py         ← app/router/stock.py (通过 import)
app/service/chat_dialogue_service.py ← app/router/chat.py (通过 import)
app/router/analysis_service.py       (兼容层 re-export)
app/router/stock_service.py          (兼容层 re-export)
app/router/chat_service.py           (兼容层 re-export)
```

依赖方向统一为：`router → service → repository`，`agent → service → repository`

---

## 预期工作量

| 操作 | 影响 |
|------|------|
| 移动 analysis_service.py | 580 行（位置移动，逻辑不变） |
| 移动 stock_service.py | 492 行（位置移动，逻辑不变） |
| 移动 chat_service.py | 258 行（位置移动，逻辑不变） |
| 创建 3 个兼容层 re-export 文件 | +15 行 |
| 修改 ~6 个文件的 import 路径 | 改 ~6 行 |
| shared.py 处理 | 视情况 0~50 行变动 |
| **净代码量变化** | **基本为 0**（只是移动位置） |
