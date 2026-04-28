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

    assert len(AGENT_TOOLS) == 12, f"期望 12 个工具，实际 {len(AGENT_TOOLS)}"
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
    assert agent.agent_mode == "kimi-react+thinking", \
        f"agent_mode 应为 kimi-react+thinking，实际: {agent.agent_mode}"
    assert agent._graph is not None, "LangGraph 图未构建"
    assert agent.tool_llm is not None, "工具调用模型未初始化"
    assert agent._thinking_client is not None, "_thinking_client 未初始化"
    assert not hasattr(agent, "answer_llm"), "旧的 answer_llm 应已移除"
    step(f"framework={agent.framework}  mode={agent.agent_mode}")
    step(f"工具调用模型={agent.tool_llm.model_name}")
    step(f"thinking 客户端={type(agent._thinking_client).__name__}")
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
    """流式 stream()：验证新事件序列 tool_call* → synthesizing → answer_chunk+ → answer_done。"""
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
        elif etype == "synthesizing":
            print(f"  [合成中] kimi-k2.5 开始生成...")
        elif etype == "answer_chunk":
            answer_chunks.append(event["content"])
            print(event["content"], end="", flush=True)
        elif etype == "answer_done":
            print()
            print(f"  [完成]")

    print()
    event_types = [e["type"] for e in events]
    step(f"共 {len(events)} 个事件: {set(event_types)}")

    assert "tool_call" in event_types, "应有 tool_call 事件"
    assert "synthesizing" in event_types, "应有 synthesizing 过渡事件"
    assert "answer_chunk" in event_types, "应有 answer_chunk 事件"
    assert "answer_done" in event_types, "应有 answer_done 结束事件"
    assert "answer" not in event_types, "旧的 answer 事件类型不应出现"
    assert len(answer_chunks) > 0, "answer_chunk 不能为空"

    # 验证事件顺序：所有 tool_call/tool_result 在 synthesizing 之前
    synth_idx = next(i for i, e in enumerate(events) if e["type"] == "synthesizing")
    for i, e in enumerate(events[:synth_idx]):
        assert e["type"] in ("tool_call", "tool_result"), \
            f"synthesizing 之前出现了非预期事件: {e['type']}"

    # answer_done 是最后一个事件
    assert events[-1]["type"] == "answer_done", \
        f"最后一个事件应为 answer_done，实际: {events[-1]['type']}"


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
    """专项验证双模型架构：工具调用用 moonshot-v1-8k，答案生成用原生 kimi-k2.5。"""
    from agent.integration.langgraph_agent import LangGraphAgent
    from openai import OpenAI

    agent = LangGraphAgent()

    assert agent.tool_llm.model_name == "moonshot-v1-8k", \
        f"工具调用模型应为 moonshot-v1-8k，实际: {agent.tool_llm.model_name}"
    assert isinstance(agent._thinking_client, OpenAI), \
        "_thinking_client 应为原生 OpenAI 实例"
    assert agent.THINKING_MODEL == "kimi-k2.5", \
        f"THINKING_MODEL 应为 kimi-k2.5，实际: {agent.THINKING_MODEL}"
    step(f"工具调用模型: {agent.tool_llm.model_name}")
    step(f"thinking 客户端: {type(agent._thinking_client).__name__}  model={agent.THINKING_MODEL}")

    assert agent.agent_mode == "kimi-react+thinking", \
        f"agent_mode 应为 kimi-react+thinking，实际: {agent.agent_mode}"
    step(f"agent_mode: {agent.agent_mode}")

    question = "恒瑞医药600276的毛利率是多少？"
    step(f"测试问题: {question}")
    result = agent.run(question)

    assert result.get("thinking_used") is True, \
        "有工具调用时 thinking_used 应为 True"
    assert len(result["answer"]) > 0, "答案不能为空"
    step(f"thinking_used={result['thinking_used']}  答案长度={len(result['answer'])}字")
    step(f"答案前100字: {result['answer'][:100]}...")



# ─────────────────────────────────────────────
# 新增用例
# ─────────────────────────────────────────────

def case_thinking_flag():
    """run() 返回 thinking_used=True，answer 非空。"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    result = agent.run("恒瑞医药600276最近的药品获批情况")

    assert isinstance(result, dict), "应返回 dict"
    assert "thinking_used" in result, "缺少 thinking_used 字段"
    assert "answer" in result, "缺少 answer 字段"
    assert result["thinking_used"] is True, \
        f"有工具调用时 thinking_used 应为 True，实际: {result['thinking_used']}"
    assert len(result["answer"]) > 0, "answer 不能为空"
    step(f"thinking_used={result['thinking_used']}  answer 长度={len(result['answer'])}字")


def case_tool_calls_structure():
    """每个 tool_call 有 tool / args / result_preview 三字段。"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    result = agent.run("恒瑞医药600276的财务状况")

    assert len(result["tool_calls"]) >= 1, "应至少调用 1 个工具"
    for tc in result["tool_calls"]:
        assert "tool" in tc, f"tool_call 缺少 tool 字段: {tc}"
        assert "args" in tc, f"tool_call 缺少 args 字段: {tc}"
        assert "result_preview" in tc, f"tool_call 缺少 result_preview 字段: {tc}"
        step(f"{tc['tool']}  preview={tc['result_preview'][:40]}")


def case_stream_events():
    """事件顺序：tool_call* → tool_result* → synthesizing → answer_chunk+ → answer_done。"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    events = list(agent.stream("恒瑞医药600276的集采风险"))
    types = [e["type"] for e in events]

    step(f"事件序列: {types}")

    assert "synthesizing" in types, "缺少 synthesizing 事件"
    assert "answer_chunk" in types, "缺少 answer_chunk 事件"
    assert "answer_done" in types, "缺少 answer_done 事件"
    assert types[-1] == "answer_done", f"最后一个事件应为 answer_done，实际: {types[-1]}"

    synth_idx = types.index("synthesizing")
    done_idx = types.index("answer_done")
    first_chunk_idx = types.index("answer_chunk")

    assert synth_idx < first_chunk_idx, "synthesizing 应在 answer_chunk 之前"
    assert first_chunk_idx < done_idx, "answer_chunk 应在 answer_done 之前"

    # synthesizing 之前只允许 tool_call / tool_result
    for t in types[:synth_idx]:
        assert t in ("tool_call", "tool_result"), \
            f"synthesizing 之前出现了非预期事件类型: {t}"


def case_stream_content():
    """所有 answer_chunk 拼接长度 > 50 字。"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    chunks = [
        e["content"]
        for e in agent.stream("恒瑞医药600276的研发费用率趋势")
        if e["type"] == "answer_chunk"
    ]

    full_answer = "".join(chunks)
    step(f"answer_chunk 数量={len(chunks)}  拼接长度={len(full_answer)}字")
    assert len(full_answer) > 50, \
        f"拼接答案长度应 > 50 字，实际: {len(full_answer)}"


def case_fallback():
    """mock _thinking_client 抛异常 → thinking_used=False，answer 非空（降级到 moonshot）。"""
    from unittest.mock import patch, MagicMock
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()

    # mock _thinking_client.chat.completions.create 抛异常
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("模拟 kimi-k2.5 不可用")

    with patch.object(agent, "_thinking_client", mock_client):
        result = agent.run("恒瑞医药600276的营收情况")

    assert isinstance(result, dict), "应返回 dict"
    assert result.get("thinking_used") is False, \
        f"kimi-k2.5 失败时 thinking_used 应为 False，实际: {result.get('thinking_used')}"
    assert len(result.get("answer", "")) > 0, "降级后 answer 不能为空"
    step(f"thinking_used={result['thinking_used']}  降级答案长度={len(result['answer'])}字")


# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────

CASES = {
    "tools":          ("工具注册验证",                case_tool_registration),
    "init":           ("Agent 初始化",                case_agent_init),
    "dual_model":     ("双模型架构验证",               case_dual_model_architecture),
    "run_code":       ("同步run - 有股票代码",         case_sync_run_with_code),
    "run_name":       ("同步run - 只有公司名",         case_sync_run_name_only),
    "stream":         ("流式stream输出",               case_stream),
    "multi_turn":     ("多轮对话",                    case_multi_turn),
    "no_data":        ("边界-无关数据",                case_no_relevant_data),
    "thinking_flag":  ("thinking_used 标志验证",       case_thinking_flag),
    "tool_struct":    ("tool_call 结构验证",           case_tool_calls_structure),
    "stream_events":  ("stream 事件顺序验证",          case_stream_events),
    "stream_content": ("stream 内容长度验证",          case_stream_content),
    "fallback":       ("kimi-k2.5 降级验证",           case_fallback),
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
