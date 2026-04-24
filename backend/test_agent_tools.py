"""
Agent 工具函数测试脚本
直接连接真实数据库，逐个测试所有 28 个工具函数。

运行方式：
    cd backend
    python test_agent_tools.py
    python test_agent_tools.py --stock 600519   # 指定股票代码
    python test_agent_tools.py --module company  # 只测某个模块
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any

# 禁止 HuggingFace 联网检查，直接用本地缓存，避免无网络环境下卡住
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")

# Windows GBK 终端下强制 UTF-8 输出，避免中文乱码
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 确保 backend 目录在 Python 路径中
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ─────────────────────────────────────────────
# 输出工具
# ─────────────────────────────────────────────

class Printer:
    PASS  = "  [PASS]"
    FAIL  = "  [FAIL]"
    SKIP  = "  [SKIP]"
    INFO  = "  [INFO]"
    SEP   = "─" * 60

    def __init__(self):
        self.results: list[dict] = []

    def section(self, title: str):
        print(f"\n{'═' * 60}")
        print(f"  {title}")
        print(f"{'═' * 60}")

    def ok(self, name: str, detail: str = ""):
        self.results.append({"name": name, "status": "PASS"})

    def fail(self, name: str, error: str):
        print(f"{self.FAIL} {name}")
        print(f"         ✗ {error}")
        self.results.append({"name": name, "status": "FAIL", "error": error})

    def skip(self, name: str, reason: str):
        print(f"{self.SKIP} {name}  ({reason})")
        self.results.append({"name": name, "status": "SKIP"})

    def info(self, msg: str):
        print(f"{self.INFO} {msg}")

    def summary(self):
        total  = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        skipped= sum(1 for r in self.results if r["status"] == "SKIP")

        print(f"\n{'═' * 60}")
        print(f"  测试结果汇总")
        print(f"{'═' * 60}")
        print(f"  总计: {total}  通过: {passed}  失败: {failed}  跳过: {skipped}")

        if failed:
            print(f"\n  失败项目:")
            for r in self.results:
                if r["status"] == "FAIL":
                    print(f"    ✗ {r['name']}: {r.get('error', '')}")

        print(f"{'═' * 60}")
        return failed == 0


p = Printer()


def run(name: str, fn, *args, check=None, **kwargs):
    """执行一个工具函数，打印 '函数名: 前20字内容'，失败时打印 [FAIL]。"""
    try:
        result = fn(*args, **kwargs)

        if check:
            check(result)

        preview = _preview(result)
        print(f"  {name}: {preview}")
        p.results.append({"name": name, "status": "PASS"})
        return result

    except AssertionError as e:
        print(f"  [FAIL] {name}: 断言失败: {e}")
        p.results.append({"name": name, "status": "FAIL", "error": str(e)})
    except Exception as e:
        print(f"  [FAIL] {name}: {type(e).__name__}: {e}")
        p.results.append({"name": name, "status": "FAIL", "error": str(e)})
        if "--verbose" in sys.argv:
            traceback.print_exc()
    return None


def _preview(result: Any) -> str:
    """提取返回值的前20字可读内容。"""
    if result is None:
        return "None"
    if isinstance(result, list):
        if not result:
            return "[]"
        first = result[0]
        text = " ".join(str(v) for v in first.values()) if isinstance(first, dict) else str(first)
    elif isinstance(result, dict):
        text = " ".join(str(v) for v in result.values())
    else:
        text = str(result)
    text = text.replace("\n", " ").strip()
    return text[:20] + ("..." if len(text) > 20 else "")


# ─────────────────────────────────────────────
# 各模块测试函数
# ─────────────────────────────────────────────

def test_company(stock_code: str):
    p.section("公司信息工具  (company_tools)")

    from agent.tools import (
        get_company_basic_info,
        get_company_overview,
        get_company_profile,
        resolve_company_from_text,
    )

    info = run(
        "get_company_basic_info",
        get_company_basic_info, stock_code,
        check=lambda r: (
            assert_field(r, "stock_code"),
            assert_field(r, "stock_name"),
        ),
    )
    if info:
        p.info(f"股票: {info.get('stock_code')}  名称: {info.get('stock_name')}  "
               f"行业: {info.get('industry_level1')} / {info.get('industry_level2')}")

    run(
        "get_company_profile",
        get_company_profile, stock_code,
    )

    overview = run(
        "get_company_overview",
        get_company_overview, stock_code,
        check=lambda r: (
            assert_field(r, "stock_code"),
            assert_field(r, "industries"),
        ),
    )
    if overview:
        p.info(f"行业分类数: {len(overview.get('industries', []))}")

    companies = run(
        "resolve_company_from_text",
        resolve_company_from_text,
        info.get("stock_name", "恒瑞") if info else "恒瑞",
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )
    if companies:
        p.info(f"识别到 {len(companies)} 家公司: "
               + ", ".join(c.get("stock_name", "") for c in companies[:3]))


def test_financial(stock_code: str):
    p.section("财务数据工具  (financial_tools)")

    from agent.tools import (
        get_balance_sheets,
        get_business_segments,
        get_cashflow_statements,
        get_financial_metrics,
        get_financial_summary,
        get_income_statements,
    )

    income = run(
        "get_income_statements",
        get_income_statements, stock_code, 4,
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )
    if income:
        latest = income[0]
        p.info(f"最新期: {latest.get('report_date')}  "
               f"营收: {_fmt_money(latest.get('revenue'))}  "
               f"净利润: {_fmt_money(latest.get('net_profit'))}")

    balance = run(
        "get_balance_sheets",
        get_balance_sheets, stock_code, 4,
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )
    if balance:
        latest = balance[0]
        p.info(f"总资产: {_fmt_money(latest.get('total_assets'))}  "
               f"总负债: {_fmt_money(latest.get('total_liabilities'))}")

    run(
        "get_cashflow_statements",
        get_cashflow_statements, stock_code, 4,
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )

    metrics = run(
        "get_financial_metrics",
        get_financial_metrics, stock_code,
        ["gross_margin", "net_margin", "roe", "rd_ratio"], 4,
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )
    if metrics:
        for m in metrics[:4]:
            p.info(f"  {m.get('metric_name')}: {m.get('metric_value')} {m.get('metric_unit', '')}")

    run(
        "get_business_segments",
        get_business_segments, stock_code, 4,
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )

    summary = run(
        "get_financial_summary",
        get_financial_summary, stock_code, 4,
        check=lambda r: (
            assert_field(r, "stock_code"),
            assert_field(r, "latest_income"),
            assert_field(r, "latest_balance"),
            assert_field(r, "latest_cashflow"),
        ),
    )
    if summary:
        p.info(f"包含字段: {list(summary.keys())}")


def test_announcement(stock_code: str):
    p.section("公告事件工具  (announcement_tools)")

    from agent.tools import (
        get_clinical_trials,
        get_company_event_summary,
        get_drug_approvals,
        get_procurement_events,
        get_raw_announcements,
        get_regulatory_risks,
        get_structured_announcements,
    )

    raw = run(
        "get_raw_announcements",
        get_raw_announcements, stock_code, 365,
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )
    if raw:
        p.info(f"近一年公告 {len(raw)} 条，最新: {raw[0].get('title', '')[:40]}")

    structured = run(
        "get_structured_announcements",
        get_structured_announcements, stock_code, 365,
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )
    if structured:
        signals = {}
        for s in structured:
            sig = s.get("signal_type", "unknown")
            signals[sig] = signals.get(sig, 0) + 1
        p.info(f"信号分布: {signals}")

    approvals = run(
        "get_drug_approvals",
        get_drug_approvals, stock_code, 365,
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )
    if approvals:
        p.info(f"药品批准 {len(approvals)} 条: "
               + ", ".join(a.get("drug_name", "") for a in approvals[:3]))

    trials = run(
        "get_clinical_trials",
        get_clinical_trials, stock_code, 365,
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )
    if trials:
        p.info(f"临床试验 {len(trials)} 条")

    run(
        "get_procurement_events",
        get_procurement_events, stock_code, 365,
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )

    run(
        "get_regulatory_risks",
        get_regulatory_risks, stock_code, 365,
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )

    event_summary = run(
        "get_company_event_summary",
        get_company_event_summary, stock_code, 365,
        check=lambda r: (
            assert_field(r, "stock_code"),
            assert_field(r, "opportunity_items"),
            assert_field(r, "risk_items"),
        ),
    )
    if event_summary:
        p.info(f"机会类: {len(event_summary.get('opportunity_items', []))}  "
               f"风险类: {len(event_summary.get('risk_items', []))}  "
               f"中性: {len(event_summary.get('neutral_items', []))}")


def test_news(stock_code: str):
    p.section("新闻舆情工具  (news_tools)")

    from agent.tools import (
        get_company_news_impact,
        get_industry_news_impact,
        get_news_by_company,
        get_news_by_industry,
        get_news_raw,
    )

    raw = run(
        "get_news_raw",
        get_news_raw, 30,
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )
    if raw:
        p.info(f"近30天新闻 {len(raw)} 条，最新: {raw[0].get('title', '')[:40]}")

    company_news = run(
        "get_news_by_company",
        get_news_by_company, stock_code, 90,
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )
    if company_news:
        directions = {}
        for n in company_news:
            d = n.get("impact_direction", "unknown")
            directions[d] = directions.get(d, 0) + 1
        p.info(f"公司新闻 {len(company_news)} 条，影响方向: {directions}")

    run(
        "get_news_by_industry",
        get_news_by_industry, "医药生物", 30,
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )

    impact = run(
        "get_company_news_impact",
        get_company_news_impact, stock_code, 90,
        check=lambda r: (
            assert_field(r, "stock_code"),
            assert_field(r, "items"),
            assert_field(r, "direction_counts"),
        ),
    )
    if impact:
        strength = impact.get('avg_impact_strength')
        strength_str = f"{strength:.3f}" if isinstance(strength, (int, float)) else "N/A"
        p.info(f"平均影响强度: {strength_str}  方向统计: {impact.get('direction_counts')}")

    industry_impact = run(
        "get_industry_news_impact",
        get_industry_news_impact, "医药生物", 30,
        check=lambda r: (
            assert_field(r, "items"),
            assert_field(r, "direction_counts"),
        ),
    )
    if industry_impact:
        p.info(f"行业新闻影响 {len(industry_impact.get('items', []))} 条")


def test_macro():
    p.section("宏观经济工具  (macro_tools)")

    from agent.tools import get_macro_indicator, get_macro_summary, list_macro_indicators

    indicator_names = ["GDP增速", "CPI", "PMI", "医药制造业增加值"]

    for name in indicator_names[:2]:
        result = run(
            f"get_macro_indicator({name})",
            get_macro_indicator, name,
        )
        if result:
            p.info(f"  {result.get('indicator_name')}: "
                   f"{result.get('value')} {result.get('unit', '')}  "
                   f"期间: {result.get('period')}")

    run(
        "list_macro_indicators",
        list_macro_indicators, indicator_names,
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )

    summary = run(
        "get_macro_summary",
        get_macro_summary, ["GDP增速", "CPI"], 6,
        check=lambda r: (
            assert_field(r, "series"),
            assert_field(r, "recent_n"),
        ),
    )
    if summary:
        series = summary.get("series", {})
        p.info(f"时间序列指标数: {len(series)}  "
               + "  ".join(f"{k}: {len(v)}期" for k, v in list(series.items())[:3]))


def test_retrieval(stock_code: str):
    p.section("向量检索工具  (retrieval_tools)")

    from agent.tools import (
        search_company_evidence,
        search_documents,
        search_news_evidence,
    )

    docs = run(
        "search_documents",
        search_documents,
        query="创新药临床试验进展",
        stock_code=stock_code,
        top_k=5,
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )
    if docs:
        for d in docs[:2]:
            score = d.get("score", d.get("metadata", {}).get("score", "N/A"))
            content = str(d.get("content") or d.get("text") or "")[:60]
            p.info(f"  score={score:.3f}  {content}..." if isinstance(score, float) else f"  {content}...")

    evidence = run(
        "search_company_evidence",
        search_company_evidence,
        query="研发管线 集采",
        stock_code=stock_code,
        top_k=5,
        check=lambda r: assert_true(isinstance(r, list), "应返回列表"),
    )
    if evidence:
        p.info(f"公司证据 {len(evidence)} 条")

    news_ev = run(
        "search_news_evidence",
        search_news_evidence,
        query="新药获批 市场准入",
        stock_code=stock_code,
        top_k=5,
        # 返回 dict（含 items 列表）或 list 均可
        check=lambda r: assert_true(isinstance(r, (list, dict)), "应返回列表或字典"),
    )
    if news_ev:
        items = news_ev.get("items", []) if isinstance(news_ev, dict) else news_ev
        p.info(f"新闻证据 {len(items)} 条")
        for n in items[:2]:
            p.info(f"  [{n.get('publish_time', '')[:10]}] {n.get('title', '')[:50]}")


def test_agent_pipeline(stock_code: str):
    """测试 Agent 完整调用链：从用户问题到最终响应。"""
    p.section("Agent 完整调用链  (GLMMinimalAgent)")

    from agent.integration.agent import LangChainAgentStub

    agent = LangChainAgentStub()
    p.info(f"framework={agent.framework}  mode={agent.agent_mode}")

    question = f"请分析一下这家公司的财务状况和研发管线"

    try:
        t0 = time.monotonic()
        result = agent.run(
            question,
            targets=[{"type": "stock", "symbol": stock_code}],
            session_id=9999,
        )
        elapsed = (time.monotonic() - t0) * 1000

        assert isinstance(result, dict), "应返回 dict"
        assert "answer" in result, "缺少 answer 字段"
        assert "suggestion" in result, "缺少 suggestion 字段"
        assert "report_markdown" in result, "缺少 report_markdown 字段"

        p.ok("agent.run()", f"耗时 {elapsed:.0f}ms  mode={result.get('agent_mode')}")
        p.info(f"answer ({len(result['answer'])}字): {result['answer'][:80]}...")
        p.info(f"suggestion: {result['suggestion'][:60]}...")
        p.info(f"report_markdown 长度: {len(result['report_markdown'])} 字")

    except AssertionError as e:
        p.fail("agent.run()", f"断言失败: {e}")
    except Exception as e:
        p.fail("agent.run()", f"{type(e).__name__}: {e}")
        if "--verbose" in sys.argv:
            traceback.print_exc()


# ─────────────────────────────────────────────
# 断言辅助
# ─────────────────────────────────────────────

def assert_field(d: dict, key: str):
    assert key in d, f"返回值缺少字段 '{key}'"

def assert_true(condition: bool, msg: str):
    assert condition, msg

def _fmt_money(value) -> str:
    if value is None:
        return "N/A"
    try:
        v = float(value)
        if abs(v) >= 1e8:
            return f"{v/1e8:.2f}亿"
        if abs(v) >= 1e4:
            return f"{v/1e4:.2f}万"
        return str(v)
    except (TypeError, ValueError):
        return str(value)


# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────

MODULE_MAP = {
    "company":      test_company,
    "financial":    test_financial,
    "announcement": test_announcement,
    "news":         test_news,
    "macro":        test_macro,
    "retrieval":    test_retrieval,
    "agent":        test_agent_pipeline,
}

def main():
    parser = argparse.ArgumentParser(description="Agent 工具函数测试脚本")
    parser.add_argument("--stock",  default="600276", help="测试用股票代码 (默认: 600276 恒瑞医药)")
    parser.add_argument("--module", default="all",    help=f"只测某个模块: {list(MODULE_MAP.keys())} 或 all")
    parser.add_argument("--verbose", action="store_true", help="失败时打印完整堆栈")
    args = parser.parse_args()

    stock_code = args.stock

    print(f"\n{'═' * 60}")
    print(f"  Agent 工具函数测试")
    print(f"  股票代码: {stock_code}")
    print(f"  模块范围: {args.module}")
    print(f"{'═' * 60}")

    modules_to_run = (
        list(MODULE_MAP.items())
        if args.module == "all"
        else [(args.module, MODULE_MAP[args.module])]
        if args.module in MODULE_MAP
        else []
    )

    if not modules_to_run:
        print(f"未知模块: {args.module}，可选: {list(MODULE_MAP.keys())}")
        sys.exit(1)

    for name, fn in modules_to_run:
        if name in ("macro", "agent"):
            fn(stock_code) if name == "agent" else fn()
        else:
            fn(stock_code)

    success = p.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
