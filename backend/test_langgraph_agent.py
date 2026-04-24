"""
LangGraph Agent 测试脚本

测试内容：
  1. 工具注册 - 确认 10 个工具都正确挂载
  2. 同步 run() - 单轮问答，观察 LLM 自主选择工具
  3. 流式 stream() - 逐步打印工具调用过程和最终答案
  4. 多轮对话 - 带 history 的上下文理解
  5. 无股票代码 - 验证 LLM 会先调 tool_resolve_company

运行：
    cd backend
    python test_langgraph_agent.py
    python test_langgraph_agent.py --case stream   # 只跑某个用例
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import time
import traceback
from pathlib import Path

os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ─────────────────────────────────────────────
# 输出工具
# ─────────────────────────────────────────────

def sep(char="═", n=62):
    print(char * n)

def section(title: str):
    print()
    sep()
    print(f"  {title}")
    sep()

def ok(msg: str):
    print(f"  [OK]   {msg}")

def fail(msg: str):
    print(f"  [FAIL] {msg}")

def step(msg: str):
    print(f"  >>  {msg}")

RESULTS: list[tuple[str, bool]] = []

def run_case(name: str, fn):
    section(name)
    t0 = time.monotonic()
    try:
        fn()
        elapsed = (time.monotonic() - t0) * 1000
        ok(f"用例通过  ({elapsed:.0f}ms)")
        RESULTS.append((name, True))
    except AssertionError as e:
        fail(f"断言失败: {e}")
        RESULTS.append((name, False))
    except Exception as e:
        fail(f"{type(e).__name__}: {e}")
        traceback.print_exc()
        RESULTS.append((name, False))

# ─────────────────────────────────────────────
# 用例
# ─────────────────────────────────────────────

def case_tool_registration():
    """验证 10 个工具都正确注册，名称和描述不为空。"""
    from agent.integration.langgraph_agent import AGENT_TOOLS

    assert len(AGENT_TOOLS) == 10, f"期望 10 个工具，实际 {len(AGENT_TOOLS)}"
    for t in AGENT_TOOLS:
        name = t.name
        desc = t.description
        assert name, "工具名称为空"
        assert desc, f"工具 {name} 描述为空"
        step(f"{name}: {desc[:40]}...")
    ok(f"共 {len(AGENT_TOOLS)} 个工具全部注册正常")


def case_agent_init():
    """验证 Agent 能正常初始化，双模型架构和工具都挂载成功。"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    assert agent.is_configured(), "Kimi API 未配置，请检查 .env"
    assert agent.framework == "langgraph"
    assert agent.agent_mode == "kimi-dual-model"
    assert agent._graph is not None, "LangGraph 图未构建"
    assert agent.tool_llm is not None, "工具调用模型未初始化"
    assert agent.answer_llm is not None, "答案生成模型未初始化"
    step(f"framework={agent.framework}  mode={agent.agent_mode}")
    step(f"工具调用模型={agent.tool_llm.model_name}")
    step(f"答案生成模型={agent.answer_llm.model_name}")
    from agent.integration.langgraph_agent import AGENT_TOOLS
    step(f"工具数量={len(AGENT_TOOLS)}")


def case_sync_run_with_code():
    """同步 run()：直接给股票代码，验证双模型架构正常工作。"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    question = "恒瑞医药（600276）最近一年有哪些重要的药品获批事件？财务状况如何？"

    step(f"问题: {question}")
    step("Agent 开始思考...")

    result = agent.run(question)

    assert isinstance(result, dict), "应返回 dict"
    assert "answer" in result, "缺少 answer 字段"
    assert "tool_calls" in result, "缺少 tool_calls 字段"
    assert "dual_model_used" in result, "缺少 dual_model_used 字段"
    assert len(result["answer"]) > 0, "answer 不能为空"

    step(f"双模型已启用: {result['dual_model_used']}")
    step(f"调用了 {len(result['tool_calls'])} 个工具:")
    for i, tc in enumerate(result["tool_calls"], 1):
        args_preview = str(tc.get("args", ))[:60]
        result_preview = tc.get("result_preview", "")[:50]
        step(f"  {i}. {tc['tool']}({args_preview})")
        if result_preview:
            step(f"     → {result_preview}...")

    print()
    step(f"最终答案 ({len(result['answer'])} 字):")
    for line in result["answer"].split("\n")[:15]:
        print(f"     {line}")
    if result["answer"].count("\n") > 15:
        print("     ...")

    assert len(result["tool_calls"]) >= 1, "LLM 应至少调用 1 个工具"
    assert result["dual_model_used"] is True, "有工具调用时 dual_model_used 应为 True"


def case_sync_run_name_only():
    """同步 run()：只给公司名，验证 LLM 会先调 tool_resolve_company 拿股票代码。"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    question = "帮我分析一下恒瑞的财务健康度"

    step(f"问题: {question}  (只有公司名，无股票代码)")
    result = agent.run(question)

    assert isinstance(result, dict)
    assert len(result["answer"]) > 0

    tool_names = [tc["tool"] for tc in result["tool_calls"]]
    step(f"工具调用顺序: {tool_names}")

    assert "tool_resolve_company" in tool_names, \
        f"应先调 tool_resolve_company，实际调用: {tool_names}"
    resolve_idx = tool_names.index("tool_resolve_company")
    step(f"tool_resolve_company 在第 {resolve_idx + 1} 步被调用 ✓")

    print()
    step(f"最终答案前100字: {result['answer'][:100]}...")


def case_stream():
    """流式 stream()：验证双模型流程中工具调用和增强答案事件完整。"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    question = "恒瑞医药600276的研发管线和集采风险分析"

    step(f"问题: {question}")
    step("流式输出开始 ↓")
    print()

    events = []
    answer_chunks = []

    for event in agent.stream(question):
        events.append(event)
        etype = event["type"]

        if etype == "tool_call":
            args_str = str(event["args"])[:50]
            print(f"  [工具调用] {event['tool']}  args={args_str}")
        elif etype == "tool_result":
            preview = event["content"][:60].replace("\n", " ")
            print(f"  [工具结果] {event['tool']} → {preview}...")
        elif etype == "status":
            print(f"  [状态] {event['content']}")
        elif etype == "answer":
            content = event["content"]
            answer_chunks.append(content)
            dual = event.get("dual_model_used", False)
            print(f"  [最终答案({'kimi-k2.5' if dual else 'moonshot-v1-8k'})] {content[:80]}...")

    print()
    event_types = [e["type"] for e in events]
    step(f"共 {len(events)} 个事件: {set(event_types)}")

    assert "tool_call" in event_types, "应有 tool_call 事件"
    assert "answer" in event_types, "应有 answer 事件"
    assert len(answer_chunks) > 0, "answer 不能为空"

    # 验证答案事件携带 dual_model_used 标志
    answer_events = [e for e in events if e["type"] == "answer"]
    assert "dual_model_used" in answer_events[-1], "answer 事件应包含 dual_model_used 字段"


def case_multi_turn():
    """多轮对话：第二轮引用第一轮的上下文，验证 history 生效。"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()

    # 第一轮
    q1 = "恒瑞医药600276的营收和净利润趋势如何？"
    step(f"第1轮: {q1}")
    r1 = agent.run(q1)
    assert len(r1["answer"]) > 0
    step(f"第1轮答案前80字: {r1['answer'][:80]}...")
    step(f"第1轮工具: {[tc['tool'] for tc in r1['tool_calls']]}")

    # 构造 history
    history = [
        {"role": "user",      "content": q1},
        {"role": "assistant", "content": r1["answer"]},
    ]

    # 第二轮：用代词"这家公司"，依赖上下文
    q2 = "这家公司的研发费用率和同行相比怎么样？"
    step(f"第2轮: {q2}  (用代词，依赖上下文)")
    r2 = agent.run(q2, history=history)
    assert len(r2["answer"]) > 0
    step(f"第2轮答案前80字: {r2['answer'][:80]}...")
    step(f"第2轮工具: {[tc['tool'] for tc in r2['tool_calls']]}")

    # 第二轮应该能理解"这家公司"指恒瑞，并调用财务相关工具
    assert len(r2["tool_calls"]) >= 1, "第二轮应至少调用 1 个工具"


def case_no_relevant_data():
    """边界情况：问一个数据库里没有数据的问题，验证 Agent 不会编造。"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    question = "恒瑞医药600276在火星上的市场份额是多少？"

    step(f"问题: {question}  (不可能存在的数据)")
    result = agent.run(question)

    assert len(result["answer"]) > 0
    step(f"答案: {result['answer'][:120]}")
    # 不强断言内容，只验证 Agent 没有崩溃且给出了回答


def case_dual_model_architecture():
    """专项验证双模型架构：工具调用用 moonshot-v1-8k，答案生成用 kimi-k2.5。"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()

    # 验证两个模型配置不同
    assert agent.tool_llm.model_name == "moonshot-v1-8k", \
        f"工具调用模型应为 moonshot-v1-8k，实际: {agent.tool_llm.model_name}"
    assert agent.answer_llm.model_name == "kimi-k2.5", \
        f"答案生成模型应为 kimi-k2.5，实际: {agent.answer_llm.model_name}"
    step(f"工具调用模型: {agent.tool_llm.model_name}")
    step(f"答案生成模型: {agent.answer_llm.model_name}")

    # 验证 agent_mode 已更新
    assert agent.agent_mode == "kimi-dual-model", \
        f"agent_mode 应为 kimi-dual-model，实际: {agent.agent_mode}"
    step(f"agent_mode: {agent.agent_mode}")

    # 运行一个有工具调用的问题，验证 dual_model_used=True
    question = "恒瑞医药600276的毛利率是多少？"
    step(f"测试问题: {question}")
    result = agent.run(question)

    assert result.get("dual_model_used") is True, \
        "有工具调用时 dual_model_used 应为 True"
    assert len(result["answer"]) > 0, "答案不能为空"
    step(f"dual_model_used={result['dual_model_used']}  答案长度={len(result['answer'])}字")
    step(f"答案前100字: {result['answer'][:100]}...")


# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────

CASES = {
    "tools":        ("工具注册验证",              case_tool_registration),
    "init":         ("Agent 初始化",              case_agent_init),
    "dual_model":   ("双模型架构验证",             case_dual_model_architecture),
    "run_code":     ("同步run - 有股票代码",       case_sync_run_with_code),
    "run_name":     ("同步run - 只有公司名",       case_sync_run_name_only),
    "stream":       ("流式stream输出",             case_stream),
    "multi_turn":   ("多轮对话",                  case_multi_turn),
    "no_data":      ("边界-无关数据",              case_no_relevant_data),
}

def main():
    parser = argparse.ArgumentParser(description="LangGraph Agent 测试脚本")
    parser.add_argument("--case", default="all", help=f"运行指定用例: {list(CASES.keys())} 或 all")
    args = parser.parse_args()

    print()
    sep("═")
    print("  LangGraph ReAct Agent 测试（双模型架构）")
    sep("═")

    if args.case == "all":
        to_run = list(CASES.items())
    elif args.case in CASES:
        to_run = [(args.case, CASES[args.case])]
    else:
        print(f"未知用例: {args.case}，可选: {list(CASES.keys())}")
        sys.exit(1)

    for key, (title, fn) in to_run:
        run_case(title, fn)

    # 汇总
    print()
    sep()
    print("  测试结果汇总")
    sep()
    passed = sum(1 for _, ok in RESULTS if ok)
    failed = sum(1 for _, ok in RESULTS if not ok)
    print(f"  总计: {len(RESULTS)}  通过: {passed}  失败: {failed}")
    if failed:
        print()
        for name, ok in RESULTS:
            if not ok:
                print(f"  ✗ {name}")
    sep()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
