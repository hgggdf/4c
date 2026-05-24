# Step 1: 清理废代码 — Codex 执行指令

## 总体目标

删除项目中从未被调用的废代码文件和未使用的组件/模块。删除后项目必须能正常启动，所有现有 import 不报错。

---

## 执行规则

- 每完成一个子步骤，返回：✅ 修改摘要、📝 关键代码片段、❓ 需确认的问题
- 遇到不确定是否有其他引用的情况，**停下来提问**，不要猜测
- 删除文件前，先用 `grep -r "文件名或类名"` 确认无引用
- 如果发现某个文件被意外引用，跳过该文件并报告

---

### Step 1.1 — 删除后端未使用的 Agent 实现

**目标文件（相对于项目根目录 `4c/`）：**

```
backend/agent/integration/react_agent.py    （528 行，完全未被调用）
backend/agent/integration/langgraph_agent.py （493 行，初始化但从未执行）
backend/agent/integration/agent.py          （47 行，仅做委托转发的空壳）
```

**具体操作：**

1. 搜索确认 `react_agent.py` 无引用：
   ```bash
   grep -r "react_agent\|ReactAgent" backend/ --include="*.py" | grep -v "react_agent.py"
   ```
   - 预期结果：**只有** `app/router/agent.py` 引用了 `ReactAgent`
   - 如果有其他引用 → 停下来报告

2. 删除 `backend/agent/integration/react_agent.py`

3. 删除 `backend/app/router/agent.py`（这是 ReactAgent 的 HTTP 入口，随之失效）

4. 搜索确认 `langgraph_agent.py` 无实际调用：
   ```bash
   grep -r "langgraph_agent\|LangGraphAgent" backend/ --include="*.py" | grep -v "langgraph_agent.py"
   ```
   - 预期：在 `dialogue_agent.py` 中有 import 但从未在运行路径中调用
   - 操作：删除 `backend/agent/integration/langgraph_agent.py`
   - 在 `dialogue_agent.py` 中移除对应的 import 行和初始化代码

5. 搜索确认 `agent.py`（LangChainAgentStub）的引用：
   ```bash
   grep -r "LangChainAgentStub\|from agent.integration.agent\|from .agent" backend/ --include="*.py" | grep -v "agent/integration/agent.py"
   ```
   - 如果有引用，将引用改为直接使用 `GLMMinimalAgent`
   - 然后删除 `backend/agent/integration/agent.py`

**修改前（dialogue_agent.py 中相关部分）：**
```python
from agent.integration.langgraph_agent import LangGraphAgent
# ...
class DialogueAgent:
    def __init__(self):
        self._langgraph = LangGraphAgent()  # 初始化但从未使用
```

**修改后：**
```python
# 删除 LangGraphAgent 的 import 和初始化
class DialogueAgent:
    def __init__(self):
        # LangGraphAgent 已移除（从未被调用）
        pass
```

**验证标准：**
- `grep -r "ReactAgent\|LangGraphAgent\|LangChainAgentStub" backend/ --include="*.py"` 返回空
- `python -c "from agent.dialogue_agent import DialogueAgent"` 无 ImportError
- `python -c "from app.router.chat import router"` 无 ImportError

---

### Step 1.2 — 删除后端未使用的 Tool 文件

**目标文件：**

```
backend/agent/tools/scoring_tools.py          （539 行）
backend/agent/tools/pharma_decision_tools.py   （254 行）
backend/agent/tools/chart_tools.py             （194 行）
backend/agent/tools/evidence_tools.py          （139 行）
backend/agent/tools/registry.py                （29 行）
```

**具体操作：**

1. 逐一确认无引用：
   ```bash
   grep -r "scoring_tools\|PharmaScorer" backend/ --include="*.py" | grep -v "scoring_tools.py"
   grep -r "pharma_decision_tools\|PharmaDecisionTool" backend/ --include="*.py" | grep -v "pharma_decision_tools.py"
   grep -r "chart_tools\|PharmaChartBuilder" backend/ --include="*.py" | grep -v "chart_tools.py"
   grep -r "evidence_tools\|PharmaEvidenceCollector\|EvidenceBundle" backend/ --include="*.py" | grep -v "evidence_tools.py"
   grep -r "from agent.tools.registry\|from .registry\|LangChainToolRegistry" backend/ --include="*.py" | grep -v "registry.py"
   ```

2. 如果 `backend/agent/tools/__init__.py` 中 re-export 了这些类，移除对应的 import 行：

   **修改前（`backend/agent/tools/__init__.py` 示例）：**
   ```python
   from .scoring_tools import PharmaScorer
   from .pharma_decision_tools import PharmaDecisionTool
   from .chart_tools import PharmaChartBuilder
   from .evidence_tools import PharmaEvidenceCollector, EvidenceBundle
   from .registry import LangChainToolRegistry
   ```

   **修改后：**
   ```python
   # 以上已删除的模块的 import 全部移除
   # 只保留实际被调用的 tool 模块导出
   ```

3. 删除上述 5 个文件

**验证标准：**
- `python -c "import agent.tools"` 无 ImportError
- `grep -r "PharmaScorer\|PharmaDecisionTool\|PharmaChartBuilder\|PharmaEvidenceCollector\|LangChainToolRegistry" backend/` 返回空

---

### Step 1.3 — 删除前端未使用的组件

**目标文件：**

```
frontend/src/components/ButterflyPanel.vue       （896 行）
frontend/src/components/PieSelector.vue          （193 行）
frontend/src/components/IndustryReportPanel.vue   （370 行）
```

**具体操作：**

1. 确认无引用：
   ```bash
   grep -r "ButterflyPanel" frontend/src/ --include="*.vue" --include="*.js" | grep -v "ButterflyPanel.vue"
   grep -r "PieSelector" frontend/src/ --include="*.vue" --include="*.js" | grep -v "PieSelector.vue"
   grep -r "IndustryReportPanel" frontend/src/ --include="*.vue" --include="*.js" | grep -v "IndustryReportPanel.vue"
   ```
   - 如果有引用 → 停下来报告，不要删除

2. 删除这 3 个文件

**验证标准：**
- 上述 grep 命令在删除后返回空
- 项目 `npm run build`（或 `npx vite build`）无报错

---

### Step 1.4 — 删除前端未使用的 API 模块

**目标文件：**

```
frontend/src/api/announcement.js
frontend/src/api/doc.js
frontend/src/api/butterfly.js
```

**具体操作：**

1. 确认无引用：
   ```bash
   grep -r "from.*api/announcement\|import.*announcement" frontend/src/ --include="*.vue" --include="*.js" | grep -v "api/announcement.js"
   grep -r "from.*api/doc\|import.*doc" frontend/src/ --include="*.vue" --include="*.js" | grep -v "api/doc.js"
   grep -r "from.*api/butterfly\|import.*butterfly" frontend/src/ --include="*.vue" --include="*.js" | grep -v "api/butterfly.js"
   ```
   - 注意：`butterfly.js` 可能只被 `ButterflyPanel.vue` 引用，而该文件已在 1.3 中删除
   - 如果 `doc.js` 被其他文件引用 → 停下来报告

2. 删除这 3 个文件

**验证标准：**
- `npx vite build` 无报错
- 无残留 import 指向已删除文件

---

### Step 1.5 — 清理 `app/router/agent.py` 路由注册

**具体操作：**

在 `backend/main.py`（或 `backend/app/bootstrap/runtime.py`）中，找到注册 agent router 的行：

```python
from app.router.agent import router as agent_router
app.include_router(agent_router)
```

删除这两行。

**验证标准：**
- `python -c "from main import app"` 或 `python main.py` 启动无报错
- `/api/agent/stream` 路由不再存在（预期行为，因为 ReactAgent 已删除）

---

## 总验证

完成以上 5 个子步骤后，执行：

```bash
# 后端
cd backend
python -c "from main import app; print('Backend OK')"

# 前端
cd ../frontend
npx vite build
```

两者均无报错即为 Step 1 完成。

---

## 预期清理量

| 位置 | 删除行数 |
|------|----------|
| react_agent.py | 528 |
| langgraph_agent.py | 493 |
| agent.py (Stub) | 47 |
| app/router/agent.py | 55 |
| scoring_tools.py | 539 |
| pharma_decision_tools.py | 254 |
| chart_tools.py | 194 |
| evidence_tools.py | 139 |
| registry.py | 29 |
| ButterflyPanel.vue | 896 |
| PieSelector.vue | 193 |
| IndustryReportPanel.vue | 370 |
| announcement.js | ~70 |
| doc.js | ~20 |
| butterfly.js | ~30 |
| **合计** | **~3857 行** |
