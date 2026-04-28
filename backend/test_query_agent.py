"""
智能问数 Agent 测试脚本

测试 10 个典型问数场景：
1. 单公司单指标
2. 单公司多指标
3. 多公司对比
4. 缺公司名（澄清）
5. 缺具体指标（澄清）
6. 三公司对比
7. 宏观+公司联合
8. 多轮对话
9. 模糊公司名
10. 无效问题

运行：
    cd backend
    python test_query_agent.py
    python test_query_agent.py --case compare  # 只跑某个用例
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

def case_single_company_single_metric():
    """单公司单指标：宁德时代2023年毛利率"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    question = "宁德时代2023年毛利率是多少？"

    step(f"问题: {question}")
    result = agent.run(question)

    assert isinstance(result, dict)
    assert "answer" in result
    assert "tool_calls" in result
    assert len(result["answer"]) > 0, "答案不能为空"
    assert len(result["tool_calls"]) >= 1, "应至少调用1个工具"

    step(f"调用了 {len(result['tool_calls'])} 个工具")
    step(f"答案前100字: {result['answer'][:100]}...")


def case_single_company_multi_metrics():
    """单公司多指标：恒瑞医药最近4期的营收和净利润"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    question = "恒瑞医药最近4期的营收和净利润分别是多少？"

    step(f"问题: {question}")
    result = agent.run(question)

    assert isinstance(result, dict)
    assert len(result["answer"]) > 0
    assert len(result["tool_calls"]) >= 1

    step(f"调用了 {len(result['tool_calls'])} 个工具")
    step(f"答案前100字: {result['answer'][:100]}...")


def case_compare_companies():
    """多公司对比：对比恒瑞医药和复星医药的ROE"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    question = "对比恒瑞医药和复星医药的ROE"

    step(f"问题: {question}")
    result = agent.run(question)

    assert isinstance(result, dict)
    assert len(result["answer"]) > 0
    assert len(result["tool_calls"]) >= 1

    # 检查是否调用了对比工具
    tool_names = [tc["tool"] for tc in result["tool_calls"]]
    step(f"工具调用: {tool_names}")

    step(f"答案前100字: {result['answer'][:100]}...")


def case_missing_company():
    """缺公司名（澄清）：营收怎么样？"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    question = "营收怎么样？"

    step(f"问题: {question}  (缺公司名)")
    result = agent.run(question)

    assert isinstance(result, dict)
    step(f"clarification_needed={result.get('clarification_needed', False)}")

    if result.get("clarification_needed"):
        step(f"澄清问题: {result.get('clarification_question', '')}")
        ok("正确识别出缺少公司名")
    else:
        step(f"答案: {result['answer'][:100]}...")


def case_missing_metric():
    """缺具体指标（澄清）：恒瑞的数据"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    question = "恒瑞的数据"

    step(f"问题: {question}  (缺具体指标)")
    result = agent.run(question)

    assert isinstance(result, dict)
    step(f"clarification_needed={result.get('clarification_needed', False)}")

    if result.get("clarification_needed"):
        step(f"澄清问题: {result.get('clarification_question', '')}")
        ok("正确识别出缺少具体指标")
    else:
        step(f"答案: {result['answer'][:100]}...")


def case_three_companies():
    """三公司对比：对比恒瑞、复星、华东医药的毛利率增长趋势"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    question = "对比恒瑞医药、复星医药、华东医药的毛利率"

    step(f"问题: {question}")
    result = agent.run(question)

    assert isinstance(result, dict)
    assert len(result["answer"]) > 0
    assert len(result["tool_calls"]) >= 1

    step(f"调用了 {len(result['tool_calls'])} 个工具")
    step(f"答案前100字: {result['answer'][:100]}...")


def case_macro_and_company():
    """宏观+公司联合：医药行业PMI和恒瑞营收的关系"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    question = "医药行业PMI和恒瑞医药营收有什么关系？"

    step(f"问题: {question}")
    result = agent.run(question)

    assert isinstance(result, dict)
    assert len(result["answer"]) > 0

    step(f"调用了 {len(result['tool_calls'])} 个工具")
    step(f"答案前100字: {result['answer'][:100]}...")


def case_multi_turn():
    """多轮对话：第1轮问营收，第2轮问同比增长"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()

    # 第1轮
    q1 = "恒瑞医药2025年营收是多少？"
    step(f"第1轮: {q1}")
    r1 = agent.run(q1)
    assert len(r1["answer"]) > 0
    step(f"第1轮答案前80字: {r1['answer'][:80]}...")

    # 第2轮
    history = [
        {"role": "user", "content": q1},
        {"role": "assistant", "content": r1["answer"]},
    ]
    q2 = "同比增长多少？"
    step(f"第2轮: {q2}  (依赖上下文)")
    r2 = agent.run(q2, history=history)
    assert len(r2["answer"]) > 0
    step(f"第2轮答案前80字: {r2['answer'][:80]}...")


def case_fuzzy_company_name():
    """模糊公司名：茅台的财务健康度"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    question = "茅台的财务健康度怎么样？"

    step(f"问题: {question}  (模糊公司名)")
    result = agent.run(question)

    assert isinstance(result, dict)
    assert len(result["answer"]) > 0

    tool_names = [tc["tool"] for tc in result["tool_calls"]]
    if "tool_resolve_company" in tool_names:
        step("正确调用了 tool_resolve_company 识别公司")

    step(f"答案前100字: {result['answer'][:100]}...")


def case_invalid_question():
    """无效问题：明天天气怎么样"""
    from agent.integration.langgraph_agent import LangGraphAgent

    agent = LangGraphAgent()
    question = "明天天气怎么样？"

    step(f"问题: {question}  (非财务问题)")
    result = agent.run(question)

    assert isinstance(result, dict)
    assert len(result["answer"]) > 0

    step(f"答案: {result['answer'][:120]}")
    # 不强断言内容，只验证 Agent 没有崩溃


# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────

CASES = {
    "single":      ("单公司单指标",              case_single_company_single_metric),
    "multi":       ("单公司多指标",              case_single_company_multi_metrics),
    "compare":     ("多公司对比",                case_compare_companies),
    "missing_co":  ("缺公司名（澄清）",          case_missing_company),
    "missing_met": ("缺具体指标（澄清）",        case_missing_metric),
    "three":       ("三公司对比",                case_three_companies),
    "macro":       ("宏观+公司联合",             case_macro_and_company),
    "multi_turn":  ("多轮对话",                  case_multi_turn),
    "fuzzy":       ("模糊公司名",                case_fuzzy_company_name),
    "invalid":     ("无效问题",                  case_invalid_question),
}

def main():
    parser = argparse.ArgumentParser(description="智能问数 Agent 测试脚本")
    parser.add_argument("--case", default="all", help=f"运行指定用例: {list(CASES.keys())} 或 all")
    args = parser.parse_args()

    print()
    sep("═")
    print("  智能问数 Agent 测试")
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
