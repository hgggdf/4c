# Step 2: 修复 Agent 模式 + 清理遗留废代码 + 消除重复函数 — Codex 执行指令

## 总体目标

1. **修复 Step 1 引入的回归**：前端 Agent 模式请求 `/api/agent/stream` 返回 404
2. 删除 Step 1 中因引用链误判而保留的废代码（现已确认整条链均未被调用）
3. 将散落在多个文件中的重复工具函数统一到公共模块

---

## 执行规则

- 每完成一个子步骤，返回：✅ 修改摘要、📝 关键代码片段、❓ 需确认的问题
- 删除前先 `grep -r` 确认无活跃引用（排除 `__pycache__` 和 `.venv`）
- 遇到不确定是否有运行时引用的情况，**停下来提问**

---

### Step 2.0 — 修复前端 Agent 模式 404（回归修复，最高优先级）

**问题描述：**

Step 1 删除了 `backend/app/router/agent.py`（ReactAgent 的 `/api/agent/stream` 路由），但前端 `ChatPanel.vue` 有 Agent 模式开关，开启后通过 `sendAgentStream()` 请求 `/api/agent/stream`，导致 404。

**根因：**
- `frontend/src/api/chat.js:113` 调用 `/api/agent/stream`
- `frontend/src/components/ChatPanel.vue:362` 在 `agentMode` 为 true 时走这条路径
- `frontend/src/store/chatStore.js:270` 的 `askAgent` action 调用 `sendAgentStream`

**修复方案：**

1. 将请求地址从 `/api/agent/stream` 改为 `/api/query/stream`
2. 在 `chatStore.js` 的 `askAgent` 中补齐对 `clarification` 事件和 `{ done: true }` 结束信号的处理

**目标文件：**
```
frontend/src/api/chat.js
frontend/src/store/chatStore.js
```

---

**操作 A：修改请求地址**

文件：`frontend/src/api/chat.js`，约 line 111-115

修改前：
```javascript
// POST /api/agent/stream — 真正的 ReAct Agent 流式接口
export function sendAgentStream(payload, onEvent) {
  return fetch('/api/agent/stream', {
```

修改后：
```javascript
// POST /api/query/stream — ReAct Agent 流式接口（LangGraph）
export function sendAgentStream(payload, onEvent) {
  return fetch('/api/query/stream', {
```

---

**操作 B：补齐 askAgent 事件处理**

文件：`frontend/src/store/chatStore.js`，`askAgent` action 内的 `onEvent` 回调（约 line 294-314）

当前代码处理了：`thinking`、`tool_call`、`tool_result`、`status`、`answer`、`answer_chunk`、`synthesizing`、`error`

需要补充处理：
1. `clarification` — 后端发出 `{ type: 'clarification', question: '...' }` 表示需要用户澄清
2. `{ done: true }` — 后端结束信号（无 `type` 字段，只有 `done: true`）

修改前（line 294-314 的 onEvent 回调）：
```javascript
(event) => {
  if (event.type === 'thinking') {
    assistantMsg.agentTrace.push({ type: 'thinking', content: event.content })
  } else if (event.type === 'tool_call') {
    assistantMsg.agentTrace.push({ type: 'tool_call', tool: event.tool, args: event.args, call_id: event.call_id })
  } else if (event.type === 'tool_result') {
    assistantMsg.agentTrace.push({ type: 'tool_result', tool: event.tool, call_id: event.call_id, source: event.source, preview: event.preview })
  } else if (event.type === 'status') {
    assistantMsg.agentTrace.push({ type: 'status', content: event.content })
  } else if (event.type === 'answer') {
    assistantMsg.content = event.content
    assistantMsg.agentSources = event.sources || []
    window.dispatchEvent(new CustomEvent('chat-scroll-bottom'))
  } else if (event.type === 'answer_chunk') {
    assistantMsg.content += event.content || ''
    window.dispatchEvent(new CustomEvent('chat-scroll-bottom'))
  } else if (event.type === 'synthesizing') {
    assistantMsg.agentTrace.push({ type: 'status', content: '正在综合分析…' })
  } else if (event.type === 'error') {
    assistantMsg.content = `[Agent 错误：${event.message}]`
  }
}
```

修改后：
```javascript
(event) => {
  if (event.done) {
    // 后端结束信号 { done: true }，忽略即可
    return
  }
  if (event.type === 'thinking') {
    assistantMsg.agentTrace.push({ type: 'thinking', content: event.content })
  } else if (event.type === 'tool_call') {
    assistantMsg.agentTrace.push({ type: 'tool_call', tool: event.tool, args: event.args, call_id: event.call_id })
  } else if (event.type === 'tool_result') {
    assistantMsg.agentTrace.push({ type: 'tool_result', tool: event.tool, call_id: event.call_id, source: event.source, preview: event.preview })
  } else if (event.type === 'status') {
    assistantMsg.agentTrace.push({ type: 'status', content: event.content })
  } else if (event.type === 'answer') {
    assistantMsg.content = event.content
    assistantMsg.agentSources = event.sources || []
    window.dispatchEvent(new CustomEvent('chat-scroll-bottom'))
  } else if (event.type === 'answer_chunk') {
    assistantMsg.content += event.content || ''
    window.dispatchEvent(new CustomEvent('chat-scroll-bottom'))
  } else if (event.type === 'synthesizing') {
    assistantMsg.agentTrace.push({ type: 'status', content: '正在综合分析…' })
  } else if (event.type === 'clarification') {
    assistantMsg.content = event.question || '请补充更多信息以便分析。'
    assistantMsg.agentTrace.push({ type: 'status', content: '需要澄清' })
    window.dispatchEvent(new CustomEvent('chat-scroll-bottom'))
  } else if (event.type === 'error') {
    assistantMsg.content = `[Agent 错误：${event.message}]`
  }
}
```

关键变更说明：
- 在回调最前面加了 `if (event.done) return` 处理 `{ done: true }` 结束信号
- 新增 `else if (event.type === 'clarification')` 分支：将澄清问题显示为 assistant 消息内容，并在 trace 中标记状态

---

**验证标准：**
```bash
# 前端构建通过
cd frontend && npx vite build

# 不再有对旧路由的引用
grep -rn "api/agent" frontend/src/ --include="*.js" --include="*.vue"
# 预期：空

# clarification 处理存在
grep -n "clarification" frontend/src/store/chatStore.js
# 预期：能找到新增的处理分支
```

功能验证（手动）：
- 切换到 Agent 模式，发送消息 → 不再 404，能收到流式响应
- 如果后端触发澄清（如问题缺少公司名），前端应显示澄清问题文本

---

### Step 2.1 — 删除未使用的 MedicalAnalyzer 及其依赖链

**背景：** `MedicalAnalyzer`（`medical_analyzer.py`）从未被 import，因此它调用的 `PharmaScorer`、`PharmaDecisionTool`、`PharmaChartBuilder`、`PharmaEvidenceCollector` 整条链都是废代码。`serialization.py` 也从未被 import。

**验证命令（先执行确认）：**
```bash
grep -rn "medical_analyzer\|MedicalAnalyzer" backend/ --include="*.py" | grep -v __pycache__ | grep -v ".venv" | grep -v "medical_analyzer.py"
# 预期：只有 pharma_decision_tools.py 中的注释引用，无实际 import

grep -rn "from.*serialization\|import.*serialization" backend/ --include="*.py" | grep -v __pycache__ | grep -v ".venv"
# 预期：空（无人 import）
```

**如果 grep 结果与预期不符 → 停下来报告**

**目标文件（删除）：**
```
backend/agent/integration/medical_analyzer.py   （整个文件，MedicalAnalyzer 从未被 import）
backend/agent/integration/serialization.py      （整个文件，safe_to_dict 的独立副本，从未被 import）
backend/agent/tools/scoring_tools.py            （PharmaScorer 仅被 medical_analyzer 和 pharma_decision_tools 使用）
backend/agent/tools/pharma_decision_tools.py    （PharmaDecisionTool 仅被 medical_analyzer 使用）
backend/agent/tools/chart_tools.py              （PharmaChartBuilder 仅被 pharma_decision_tools 使用）
backend/agent/tools/evidence_tools.py           （PharmaEvidenceCollector 仅被 pharma_decision_tools 使用）
```

**同时修改 `__init__.py` 文件：**

在 `backend/agent/tools/__init__.py` 中，如果存在对以上模块的 import 或 re-export，删除对应行。

在 `backend/agent/integration/__init__.py` 中，如果存在对 `medical_analyzer` 或 `serialization` 的 import，删除对应行。

**验证标准：**
```bash
grep -rn "PharmaScorer\|PharmaDecisionTool\|PharmaChartBuilder\|PharmaEvidenceCollector\|MedicalAnalyzer\|EvidenceBundle" backend/ --include="*.py" | grep -v __pycache__ | grep -v ".venv"
# 预期：空

python -c "import agent.tools; print('OK')"
python -c "from agent.integration.glm_agent import GLMMinimalAgent; print('OK')"
```

---

### Step 2.2 — 提取 `safe_to_dict` 到统一位置

**当前状况：** `safe_to_dict` 在 3 个文件中有完全相同的定义：
- `backend/agent/integration/medical_adapter.py:20`
- `backend/agent/integration/serialization.py:7`（将在 2.1 中删除）
- `backend/agent/integration/tool_executor.py:10`

**具体操作：**

1. 新建 `backend/app/core/utils/convert.py`
2. 将 `safe_to_dict` 函数写入该文件：

```python
# backend/app/core/utils/convert.py
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def safe_to_dict(value: Any) -> Any:
    try:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if is_dataclass(value):
            return safe_to_dict(asdict(value))
        if isinstance(value, list):
            return [safe_to_dict(item) for item in value]
        if isinstance(value, dict):
            return {str(key): safe_to_dict(item) for key, item in value.items()}
        if hasattr(value, "model_dump"):
            try:
                return safe_to_dict(value.model_dump())
            except Exception:
                pass
        if hasattr(value, "dict"):
            try:
                return safe_to_dict(value.dict())
            except Exception:
                pass
        return {"repr": str(value)}
    except Exception:
        try:
            return {"repr": str(value)}
        except Exception:
            return {"repr": "<unserializable>"}
```

3. 修改引用方（删除本地定义，替换为 import）：

**`backend/agent/integration/medical_adapter.py`**
```python
# 修改前（line 20 起，约 15 行函数定义）：
def safe_to_dict(value: Any) -> Any:
    ...

# 修改后（替换为一行 import）：
from app.core.utils.convert import safe_to_dict
```

**`backend/agent/integration/tool_executor.py`**
```python
# 修改前（line 10 起，约 15 行函数定义）：
def safe_to_dict(value: Any) -> Any:
    ...

# 修改后（替换为一行 import）：
from app.core.utils.convert import safe_to_dict
```

**验证标准：**
```bash
# 确认只剩一个定义
grep -rn "^def safe_to_dict" backend/ --include="*.py" | grep -v __pycache__ | grep -v ".venv"
# 预期：只有 app/core/utils/convert.py 一处

python -c "from app.core.utils.convert import safe_to_dict; print(safe_to_dict({'a': 1}))"
python -c "from agent.integration.tool_executor import execute_tool_plan; print('OK')"
python -c "from agent.integration.medical_adapter import build_medical_analysis; print('OK')"
```

---

### Step 2.3 — 提取 `_compact_text` 到统一位置

**当前状况：** 3 处定义（签名略有不同）：
- `backend/agent/dialogue_agent.py:19` — `_compact_text(value, *, limit=180)`
- `backend/agent/integration/glm_agent.py:36` — `_compact_text(value, *, limit=180)`
- `backend/agent/prompts/chat_prompt.py:8` — `_compact_text(value, *, limit)` （无默认值）

**具体操作：**

1. 新建 `backend/app/core/utils/text.py`：

```python
# backend/app/core/utils/text.py
from __future__ import annotations

import re
from typing import Any


def compact_text(value: Any, *, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."
```

注意：函数名从 `_compact_text` 改为 `compact_text`（去掉下划线前缀，因为它现在是公共 API）。

2. 修改 3 个文件（删除本地定义，import 并起别名）：

**`backend/agent/dialogue_agent.py`**
```python
# 修改前（line 19-23）：
def _compact_text(value: Any, *, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    ...

# 修改后（替换为 import，保留内部别名避免修改所有调用点）：
from app.core.utils.text import compact_text as _compact_text
```

**`backend/agent/integration/glm_agent.py`**
```python
# 修改前（line 36-40）：
def _compact_text(value: Any, *, limit: int = 180) -> str:
    ...

# 修改后：
from app.core.utils.text import compact_text as _compact_text
```

**`backend/agent/prompts/chat_prompt.py`**
```python
# 修改前（line 8-12）：
def _compact_text(value: Any, *, limit: int) -> str:
    ...

# 修改后（公共版本有默认值 180，兼容无默认值场景）：
from app.core.utils.text import compact_text as _compact_text
```

**验证标准：**
```bash
grep -rn "^def _compact_text\|^def compact_text" backend/ --include="*.py" | grep -v __pycache__ | grep -v ".venv"
# 预期：只有 app/core/utils/text.py 一处

python -c "from app.core.utils.text import compact_text; print(compact_text('hello world  test', limit=10))"
python -c "from agent.dialogue_agent import DialogueAgent; print('OK')"
python -c "from agent.integration.glm_agent import GLMMinimalAgent; print('OK')"
```

---

### Step 2.4 — 提取 `_to_float` 到统一位置

**当前状况：** 4 处定义（3 处将在 2.1 中随文件删除，剩 1 处活跃）：
- `backend/agent/integration/medical_analyzer.py:35` — 将在 2.1 删除
- `backend/agent/tools/pharma_decision_tools.py:244` — 将在 2.1 删除
- `backend/agent/tools/scoring_tools.py:46` — 将在 2.1 删除
- `backend/app/service/butterfly_service.py:151` — **活跃**

**具体操作：**

1. 在 `backend/app/core/utils/convert.py`（Step 2.2 已创建）中追加：

```python
def to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
```

2. 修改活跃引用方：

**`backend/app/service/butterfly_service.py`**
```python
# 修改前（line 151 起，约 5 行函数定义）：
def _to_float(val: Any) -> float | None:
    ...

# 修改后：
from app.core.utils.convert import to_float as _to_float
```

**验证标准：**
```bash
grep -rn "^def _to_float\|^def to_float" backend/ --include="*.py" | grep -v __pycache__ | grep -v ".venv"
# 预期：只有 app/core/utils/convert.py 一处

python -c "from app.core.utils.convert import to_float; print(to_float('3.14'), to_float(None))"
python -c "from app.service.butterfly_service import ButterflyService; print('OK')"
```

---

### Step 2.5 — 提取 `_latest_by_year` / `_latest_rows_by_year` 到统一位置

**当前状况：** 两个方法逻辑相同，名字不同：
- `backend/app/router/analysis_service.py:393` — `_latest_by_year(self, rows, year_attr)`
- `backend/app/router/stock_service.py:486` — `_latest_rows_by_year(self, rows, year_attr)`

**具体操作：**

1. **先读取两个方法的完整实现**，确认逻辑一致。如果有差异 → **停下来报告，不要猜测**。

2. 新建 `backend/app/core/utils/query.py`，将统一后的函数写入：

```python
# backend/app/core/utils/query.py
from __future__ import annotations
from typing import Any, Iterable

def latest_rows_by_year(rows: Iterable, year_attr: str) -> dict[int, Any]:
    # 实现从两个方法中提取 — Codex 必须先读取原始代码确认
    ...
```

> ⚠️ Codex 必须先读 `analysis_service.py:393-410` 和 `stock_service.py:486-500` 的完整代码，确认逻辑一致后再写统一版本。

3. 替换两处引用：

**`backend/app/router/analysis_service.py`**
```python
# 删除 _latest_by_year 方法定义
# 在类中需要调用时改为：
from app.core.utils.query import latest_rows_by_year
# 将 self._latest_by_year(...) 替换为 latest_rows_by_year(...)
```

**`backend/app/router/stock_service.py`**
```python
# 删除 _latest_rows_by_year 方法定义
# 将 self._latest_rows_by_year(...) 替换为 latest_rows_by_year(...)
```

**验证标准：**
```bash
grep -rn "def _latest_by_year\|def _latest_rows_by_year" backend/ --include="*.py" | grep -v __pycache__ | grep -v ".venv"
# 预期：空（方法定义已移除）

python -c "from app.router.analysis_service import AnalysisService; print('OK')"
python -c "from app.router.stock_service import StockService; print('OK')"
```

---

## 总验证

完成以上所有子步骤后，执行：

```bash
# 后端启动检查
cd backend
python -c "from main import app; print('Backend OK')"

# 废代码彻底清除
grep -rn "PharmaScorer\|PharmaDecisionTool\|PharmaChartBuilder\|PharmaEvidenceCollector\|MedicalAnalyzer" backend/ --include="*.py" | grep -v __pycache__ | grep -v ".venv"
# 预期：空

# 重复函数消除
grep -rn "^def safe_to_dict\|^def _compact_text\|^def _to_float\|^def _latest_by_year\|^def _latest_rows_by_year" backend/ --include="*.py" | grep -v __pycache__ | grep -v ".venv"
# 预期：每个函数只在 app/core/utils/ 下出现一次

# 前端构建
cd ../frontend
npx vite build
# 预期：无报错

# 前端 Agent 模式功能验证
grep -n "api/agent" frontend/src/ -r
# 预期：空（不再有对 /api/agent/stream 的引用）
```

---

## 预期清理量

| 操作 | 影响 |
|------|------|
| 修复 chat.js Agent 路由 | 改 1 行 |
| 删除 medical_analyzer.py | ~600 行 |
| 删除 serialization.py | 33 行 |
| 删除 scoring_tools.py | 539 行 |
| 删除 pharma_decision_tools.py | 254 行 |
| 删除 chart_tools.py | 194 行 |
| 删除 evidence_tools.py | 139 行 |
| 新建 convert.py + text.py + query.py | +80 行 |
| 替换重复定义 → import | 约 -120 行 |
| **净减** | **~1800 行** |
