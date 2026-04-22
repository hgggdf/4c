"""Agent工具函数真实数据测试 - 独立运行脚本"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_company_tools():
    """测试公司信息工具"""
    print("\n=== Company Tools ===")
    from agent.tools import (
        get_company_basic_info,
        get_company_profile,
        get_company_overview,
        resolve_company_from_text,
    )

    # Test 1: get_company_basic_info
    try:
        result = get_company_basic_info("600276")
        assert result["stock_code"] == "600276"
        print(f"[OK] get_company_basic_info: {result['stock_name']}")
    except Exception as e:
        print(f"[FAIL] get_company_basic_info: {e}")

    # Test 2: get_company_profile
    try:
        result = get_company_profile("600276")
        if result:
            assert result["stock_code"] == "600276"
            print(f"[OK] get_company_profile: has data")
        else:
            print("[OK] get_company_profile: no profile (normal)")
    except Exception as e:
        print(f"[FAIL] get_company_profile: {e}")

    # Test 3: get_company_overview
    try:
        result = get_company_overview("600276")
        assert result["stock_code"] == "600276"
        print(f"[OK] get_company_overview: {result['stock_name']}, industries={len(result.get('industries', []))}")
    except Exception as e:
        print(f"[FAIL] get_company_overview: {e}")

    # Test 4: resolve_company_from_text
    try:
        result = resolve_company_from_text("恒瑞")
        assert isinstance(result, list)
        print(f"[OK] resolve_company_from_text: found {len(result)} companies")
    except Exception as e:
        print(f"[FAIL] resolve_company_from_text: {e}")


def test_financial_tools():
    """测试财务数据工具"""
    print("\n=== Financial Tools ===")
    from agent.tools import (
        get_income_statements,
        get_balance_sheets,
        get_cashflow_statements,
        get_financial_metrics,
        get_business_segments,
        get_financial_summary,
    )

    # Test 1: get_income_statements
    try:
        result = get_income_statements("600276", limit=4)
        print(f"[OK] get_income_statements: {len(result)} periods")
    except Exception as e:
        print(f"[FAIL] get_income_statements: {e}")

    # Test 2: get_balance_sheets
    try:
        result = get_balance_sheets("600276", limit=4)
        print(f"[OK] get_balance_sheets: {len(result)} periods")
    except Exception as e:
        print(f"[FAIL] get_balance_sheets: {e}")

    # Test 3: get_cashflow_statements
    try:
        result = get_cashflow_statements("600276", limit=4)
        print(f"[OK] get_cashflow_statements: {len(result)} periods")
    except Exception as e:
        print(f"[FAIL] get_cashflow_statements: {e}")

    # Test 4: get_financial_metrics
    try:
        result = get_financial_metrics("600276", ["gross_margin", "net_margin"], limit=4)
        print(f"[OK] get_financial_metrics: {len(result)} records")
    except Exception as e:
        print(f"[FAIL] get_financial_metrics: {e}")

    # Test 5: get_business_segments
    try:
        result = get_business_segments("600276", limit=4)
        print(f"[OK] get_business_segments: {len(result)} segments")
    except Exception as e:
        print(f"[FAIL] get_business_segments: {e}")

    # Test 6: get_financial_summary
    try:
        result = get_financial_summary("600276", period_count=4)
        assert result["stock_code"] == "600276"
        print(f"[OK] get_financial_summary: complete")
    except Exception as e:
        print(f"[FAIL] get_financial_summary: {e}")


def test_announcement_tools():
    """测试公告事件工具"""
    print("\n=== Announcement Tools ===")
    from agent.tools import (
        get_raw_announcements,
        get_structured_announcements,
        get_drug_approvals,
        get_clinical_trials,
        get_procurement_events,
        get_regulatory_risks,
        get_company_event_summary,
    )

    # Test 1: get_raw_announcements
    try:
        result = get_raw_announcements("600276", days=365)
        print(f"[OK] get_raw_announcements: {len(result)} announcements")
    except Exception as e:
        print(f"[FAIL] get_raw_announcements: {e}")

    # Test 2: get_structured_announcements
    try:
        result = get_structured_announcements("600276", days=365)
        print(f"[OK] get_structured_announcements: {len(result)} structured")
    except Exception as e:
        print(f"[FAIL] get_structured_announcements: {e}")

    # Test 3: get_drug_approvals
    try:
        result = get_drug_approvals("600276", days=365)
        print(f"[OK] get_drug_approvals: {len(result)} approvals")
    except Exception as e:
        print(f"[FAIL] get_drug_approvals: {e}")

    # Test 4: get_clinical_trials
    try:
        result = get_clinical_trials("600276", days=365)
        print(f"[OK] get_clinical_trials: {len(result)} trials")
    except Exception as e:
        print(f"[FAIL] get_clinical_trials: {e}")

    # Test 5: get_procurement_events
    try:
        result = get_procurement_events("600276", days=365)
        print(f"[OK] get_procurement_events: {len(result)} events")
    except Exception as e:
        print(f"[FAIL] get_procurement_events: {e}")

    # Test 6: get_regulatory_risks
    try:
        result = get_regulatory_risks("600276", days=365)
        print(f"[OK] get_regulatory_risks: {len(result)} risks")
    except Exception as e:
        print(f"[FAIL] get_regulatory_risks: {e}")

    # Test 7: get_company_event_summary
    try:
        result = get_company_event_summary("600276", days=365)
        assert result["stock_code"] == "600276"
        print(f"[OK] get_company_event_summary: opportunities={len(result['opportunity_items'])}, risks={len(result['risk_items'])}")
    except Exception as e:
        print(f"[FAIL] get_company_event_summary: {e}")


def test_news_tools():
    """测试新闻舆情工具"""
    print("\n=== News Tools ===")
    from agent.tools import (
        get_news_raw,
        get_news_by_company,
        get_news_by_industry,
        get_company_news_impact,
        get_industry_news_impact,
    )

    # Test 1: get_news_raw
    try:
        result = get_news_raw(days=30)
        print(f"[OK] get_news_raw: {len(result)} news")
    except Exception as e:
        print(f"[FAIL] get_news_raw: {e}")

    # Test 2: get_news_by_company
    try:
        result = get_news_by_company("600276", days=90)
        print(f"[OK] get_news_by_company: {len(result)} company news")
    except Exception as e:
        print(f"[FAIL] get_news_by_company: {e}")

    # Test 3: get_news_by_industry
    try:
        result = get_news_by_industry("医药生物", days=90)
        print(f"[OK] get_news_by_industry: {len(result)} industry news")
    except Exception as e:
        print(f"[FAIL] get_news_by_industry: {e}")

    # Test 4: get_company_news_impact
    try:
        result = get_company_news_impact("600276", days=90)
        assert result["stock_code"] == "600276"
        print(f"[OK] get_company_news_impact: {len(result['items'])} items")
    except Exception as e:
        print(f"[FAIL] get_company_news_impact: {e}")

    # Test 5: get_industry_news_impact
    try:
        result = get_industry_news_impact("医药生物", days=90)
        assert "industry_code" in result or "days" in result
        print(f"[OK] get_industry_news_impact: {len(result.get('items', []))} items")
    except Exception as e:
        print(f"[FAIL] get_industry_news_impact: {e}")


def test_macro_tools():
    """测试宏观指标工具"""
    print("\n=== Macro Tools ===")
    from agent.tools import (
        get_macro_indicator,
        list_macro_indicators,
        get_macro_summary,
    )

    # Test 1: get_macro_indicator
    try:
        result = get_macro_indicator("GDP")
        print(f"[OK] get_macro_indicator: result={'exists' if result else 'none'}")
    except Exception as e:
        print(f"[FAIL] get_macro_indicator: {e}")

    # Test 2: list_macro_indicators
    try:
        result = list_macro_indicators(["GDP", "CPI"])
        print(f"[OK] list_macro_indicators: {len(result)} indicators")
    except Exception as e:
        print(f"[FAIL] list_macro_indicators: {e}")

    # Test 3: get_macro_summary
    try:
        result = get_macro_summary(["GDP", "CPI"], recent_n=6)
        print(f"[OK] get_macro_summary: {len(result.get('series', {}))} series")
    except Exception as e:
        print(f"[FAIL] get_macro_summary: {e}")


def test_retrieval_tools():
    """测试向量检索工具"""
    print("\n=== Retrieval Tools ===")
    from agent.tools import (
        search_documents,
        search_company_evidence,
        search_news_evidence,
    )

    # Test 1: search_documents
    try:
        result = search_documents("创新药临床试验", stock_code="600276", top_k=5)
        assert isinstance(result, list)
        print(f"[OK] search_documents: {len(result)} results")
    except Exception as e:
        print(f"[FAIL] search_documents: {e}")

    # Test 2: search_company_evidence
    try:
        result = search_company_evidence("研发管线", stock_code="600276", top_k=5)
        assert isinstance(result, list)
        print(f"[OK] search_company_evidence: {len(result)} evidence")
    except Exception as e:
        print(f"[FAIL] search_company_evidence: {e}")

    # Test 3: search_news_evidence
    try:
        result = search_news_evidence("新药研发", stock_code="600276", top_k=5)
        # search_news_evidence 返回 dict，不是 list
        if isinstance(result, dict):
            items = result.get("items", [])
            print(f"[OK] search_news_evidence: {len(items)} results")
        else:
            print(f"[OK] search_news_evidence: {len(result)} results")
    except Exception as e:
        print(f"[FAIL] search_news_evidence: {e}")


def test_prompt_templates():
    """测试提示词模板"""
    print("\n=== Prompt Templates ===")
    from agent.prompts import PromptTemplates

    # Test 1: SYSTEM_BASE
    try:
        assert len(PromptTemplates.SYSTEM_BASE) > 0
        print(f"[OK] SYSTEM_BASE: {len(PromptTemplates.SYSTEM_BASE)} chars")
    except Exception as e:
        print(f"[FAIL] SYSTEM_BASE: {e}")

    # Test 2: build_company_analysis_prompt
    try:
        prompt = PromptTemplates.build_company_analysis_prompt("600276", "恒瑞医药")
        assert "600276" in prompt
        print(f"[OK] build_company_analysis_prompt: {len(prompt)} chars")
    except Exception as e:
        print(f"[FAIL] build_company_analysis_prompt: {e}")

    # Test 3: build_financial_analysis_prompt
    try:
        prompt = PromptTemplates.build_financial_analysis_prompt("600276", "恒瑞医药")
        print(f"[OK] build_financial_analysis_prompt: {len(prompt)} chars")
    except Exception as e:
        print(f"[FAIL] build_financial_analysis_prompt: {e}")

    # Test 4: build_drug_pipeline_prompt
    try:
        prompt = PromptTemplates.build_drug_pipeline_prompt("600276", "恒瑞医药")
        print(f"[OK] build_drug_pipeline_prompt: {len(prompt)} chars")
    except Exception as e:
        print(f"[FAIL] build_drug_pipeline_prompt: {e}")

    # Test 5: build_policy_impact_prompt
    try:
        prompt = PromptTemplates.build_policy_impact_prompt("600276", "恒瑞医药")
        print(f"[OK] build_policy_impact_prompt: {len(prompt)} chars")
    except Exception as e:
        print(f"[FAIL] build_policy_impact_prompt: {e}")

    # Test 6: build_industry_comparison_prompt
    try:
        prompt = PromptTemplates.build_industry_comparison_prompt("600276", "恒瑞医药")
        print(f"[OK] build_industry_comparison_prompt: {len(prompt)} chars")
    except Exception as e:
        print(f"[FAIL] build_industry_comparison_prompt: {e}")

    # Test 7: build_risk_warning_prompt
    try:
        prompt = PromptTemplates.build_risk_warning_prompt("600276", "恒瑞医药")
        print(f"[OK] build_risk_warning_prompt: {len(prompt)} chars")
    except Exception as e:
        print(f"[FAIL] build_risk_warning_prompt: {e}")

    # Test 8: build_quick_query_prompt
    try:
        prompt = PromptTemplates.build_quick_query_prompt("恒瑞医药最近有哪些新药获批？")
        print(f"[OK] build_quick_query_prompt: {len(prompt)} chars")
    except Exception as e:
        print(f"[FAIL] build_quick_query_prompt: {e}")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Agent Tools Real Data Test")
    print("=" * 60)

    test_company_tools()
    test_financial_tools()
    test_announcement_tools()
    test_news_tools()
    test_macro_tools()
    test_retrieval_tools()
    test_prompt_templates()

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
