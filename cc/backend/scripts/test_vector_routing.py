"""
测试向量路由改动：
1. 工具路由逻辑（纯逻辑，无需数据库）
2. AGENT_TOOLS 注册完整性
3. search_documents 全库检索（需要数据库）
4. tool_search_knowledge 端到端
5. ReactAgent 执行器修复验证
"""

from __future__ import annotations

import sys
import os

# 确保从 backend 根目录运行
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
SKIP = "\033[93mSKIP\033[0m"


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check(label: str, ok: bool, detail: str = "") -> None:
    status = PASS if ok else FAIL
    line = f"  [{status}] {label}"
    if detail:
        line += f"  — {detail}"
    print(line)


# ─────────────────────────────────────────────────────────────
# 1. 工具路由逻辑（纯逻辑）
# ─────────────────────────────────────────────────────────────

def test_routing_logic() -> None:
    section("1. 工具路由逻辑（纯逻辑，无需数据库）")

    # 验证 langgraph_agent 中 tool_search_knowledge 存在且可导入
    try:
        from agent.integration.langgraph_agent import tool_search_knowledge
        check("tool_search_knowledge 可从 langgraph_agent 导入", True)
    except ImportError as e:
        check("tool_search_knowledge 可从 langgraph_agent 导入", False, str(e))
        return

    # 验证函数签名包含 doc_types 和 industry_code
    import inspect
    sig = inspect.signature(tool_search_knowledge.func if hasattr(tool_search_knowledge, "func") else tool_search_knowledge)
    params = set(sig.parameters.keys())
    check("tool_search_knowledge 有 doc_types 参数", "doc_types" in params, str(params))
    check("tool_search_knowledge 有 industry_code 参数", "industry_code" in params, str(params))
    check("tool_search_knowledge 有 query 参数", "query" in params, str(params))
    check("tool_search_knowledge 无需 stock_code（非必填）", "stock_code" not in params, str(params))

    # 验证 react_agent search_documents schema 包含新参数
    from agent.integration.react_agent import TOOLS_SCHEMA
    sd_schema = next((t for t in TOOLS_SCHEMA if t["function"]["name"] == "search_documents"), None)
    check("react_agent TOOLS_SCHEMA 中存在 search_documents", sd_schema is not None)
    if sd_schema:
        props = sd_schema["function"]["parameters"]["properties"]
        check("search_documents schema 有 doc_types", "doc_types" in props, str(list(props.keys())))
        check("search_documents schema 有 industry_code", "industry_code" in props, str(list(props.keys())))
        required = sd_schema["function"]["parameters"].get("required", [])
        check("search_documents schema 中 stock_code 非必填", "stock_code" not in required, str(required))


# ─────────────────────────────────────────────────────────────
# 2. AGENT_TOOLS 注册完整性
# ─────────────────────────────────────────────────────────────

def test_agent_tools_registration() -> None:
    section("2. AGENT_TOOLS 注册完整性")

    from agent.integration.langgraph_agent import AGENT_TOOLS

    tool_names = [t.name for t in AGENT_TOOLS]
    check("tool_search_knowledge 已注册到 AGENT_TOOLS", "tool_search_knowledge" in tool_names, str(tool_names))
    check("tool_search_company_evidence 仍保留", "tool_search_company_evidence" in tool_names)
    check("tool_resolve_company 仍保留", "tool_resolve_company" in tool_names)

    expected = {
        "tool_resolve_company",
        "tool_get_company_overview",
        "tool_get_financial_summary",
        "tool_get_financial_metrics",
        "tool_get_company_event_summary",
        "tool_get_drug_approvals",
        "tool_get_clinical_trials",
        "tool_get_company_news_impact",
        "tool_search_company_evidence",
        "tool_search_knowledge",
        "tool_get_macro_summary",
        "tool_compare_companies",
    }
    missing = expected - set(tool_names)
    check("所有预期工具均已注册", len(missing) == 0, f"缺失: {missing}" if missing else "")


# ─────────────────────────────────────────────────────────────
# 3. search_documents 全库检索（需要数据库）
# ─────────────────────────────────────────────────────────────

def test_search_documents_no_stock_code() -> None:
    section("3. search_documents 全库检索（需要数据库）")

    try:
        from agent.tools.retrieval_tools import search_documents
    except ImportError as e:
        print(f"  [{SKIP}] 导入失败，跳过: {e}")
        return

    try:
        results = search_documents("集采对仿制药的影响", top_k=3)
        check("无 stock_code 调用不抛异常", True)
        check("返回列表类型", isinstance(results, list), type(results).__name__)
        if results:
            first = results[0]
            check("结果包含 text 字段", "text" in first, str(list(first.keys())))
            check("结果包含 score 字段", "score" in first, str(list(first.keys())))
            print(f"    返回 {len(results)} 条结果，首条 score={first.get('score', 'N/A'):.4f}")
        else:
            print(f"  [{SKIP}] 向量库为空，返回0条结果（属正常）")
    except Exception as e:
        err = str(e)
        if "数据库" in err or "connect" in err.lower() or "connection" in err.lower():
            print(f"  [{SKIP}] 数据库未连接，跳过: {err[:80]}")
        else:
            check("无 stock_code 调用不抛异常", False, err[:120])

    # 验证 doc_types 过滤参数能正常传入
    try:
        results2 = search_documents(
            "医保谈判政策",
            doc_types=["announcement", "news"],
            top_k=3,
        )
        check("doc_types 过滤参数正常传入", True)
        print(f"    doc_types 过滤返回 {len(results2)} 条结果")
    except Exception as e:
        err = str(e)
        if "数据库" in err or "connect" in err.lower() or "connection" in err.lower():
            print(f"  [{SKIP}] 数据库未连接，跳过 doc_types 测试")
        else:
            check("doc_types 过滤参数正常传入", False, err[:120])


# ─────────────────────────────────────────────────────────────
# 4. tool_search_knowledge 端到端
# ─────────────────────────────────────────────────────────────

def test_tool_search_knowledge_e2e() -> None:
    section("4. tool_search_knowledge 端到端调用")

    try:
        from agent.integration.langgraph_agent import tool_search_knowledge
    except ImportError as e:
        print(f"  [{SKIP}] 导入失败: {e}")
        return

    # 调用方式：LangChain @tool 包装后通过 .invoke() 调用
    try:
        results = tool_search_knowledge.invoke({
            "query": "集采对仿制药行业的影响",
            "doc_types": ["announcement", "news"],
            "top_k": 3,
        })
        check("tool_search_knowledge.invoke 不抛异常", True)
        check("返回列表类型", isinstance(results, list), type(results).__name__)
        print(f"    返回 {len(results)} 条结果")
    except Exception as e:
        err = str(e)
        if "数据库" in err or "connect" in err.lower() or "connection" in err.lower():
            print(f"  [{SKIP}] 数据库未连接，跳过: {err[:80]}")
        else:
            check("tool_search_knowledge.invoke 不抛异常", False, err[:120])

    # 验证不传 doc_types 也能正常调用
    try:
        results2 = tool_search_knowledge.invoke({"query": "医保政策"})
        check("不传 doc_types 时调用正常", True)
    except Exception as e:
        err = str(e)
        if "数据库" in err or "connect" in err.lower() or "connection" in err.lower():
            print(f"  [{SKIP}] 数据库未连接，跳过无 doc_types 测试")
        else:
            check("不传 doc_types 时调用正常", False, err[:120])


# ─────────────────────────────────────────────────────────────
# 5. ReactAgent 执行器修复验证
# ─────────────────────────────────────────────────────────────

def test_react_agent_executor_fix() -> None:
    section("5. ReactAgent 执行器修复验证")

    import inspect
    try:
        import agent.integration.react_agent as ra_module
        source = inspect.getsource(ra_module)
    except Exception as e:
        check("读取 react_agent 源码", False, str(e))
        return

    # 确认旧的错误调用已消失
    old_call = 'search_company_evidence(args["query"], stock_code=stock_code'
    check(
        "search_documents 分支不再调用 search_company_evidence",
        old_call not in source,
        "仍含旧调用" if old_call in source else "",
    )

    # 确认新的正确调用存在
    new_import = "from agent.tools.retrieval_tools import search_documents"
    check(
        "search_documents 分支正确导入 retrieval_tools.search_documents",
        new_import in source,
        "未找到正确导入" if new_import not in source else "",
    )

    # 确认 doc_types 参数被传递
    check(
        "执行器传递 doc_types 参数",
        'doc_types=args.get("doc_types")' in source,
        "未找到 doc_types 传递" if 'doc_types=args.get("doc_types")' not in source else "",
    )

    # 确认 system prompt 包含工具选择指引
    check(
        "SYSTEM_PROMPT 包含行业问题路由指引",
        "search_documents" in source and "行业" in source,
    )


# ─────────────────────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n向量路由改动测试")

    test_routing_logic()
    test_agent_tools_registration()
    test_search_documents_no_stock_code()
    test_tool_search_knowledge_e2e()
    test_react_agent_executor_fix()

    print(f"\n{'='*60}")
    print("  测试完成")
    print(f"{'='*60}\n")
