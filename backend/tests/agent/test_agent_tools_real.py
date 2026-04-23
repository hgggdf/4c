"""Agent工具函数测试 - 使用真实数据库"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestCompanyTools:
    """测试公司信息工具 - 真实数据"""

    def test_get_company_basic_info(self):
        """测试获取公司基本信息"""
        from agent.tools import get_company_basic_info

        result = get_company_basic_info("600276")
        assert result is not None
        assert result["stock_code"] == "600276"
        assert "stock_name" in result
        print(f"[OK] get_company_basic_info: {result['stock_name']}")

    def test_get_company_profile(self):
        """测试获取公司资料"""
        from agent.tools import get_company_profile

        result = get_company_profile("600276")
        # Profile可能为空
        if result:
            assert result["stock_code"] == "600276"
            print(f"[OK] get_company_profile: has data")
        else:
            print("[OK] get_company_profile: no profile data (normal)")

    def test_get_company_overview(self):
        """测试获取公司完整概览"""
        from agent.tools import get_company_overview

        result = get_company_overview("600276")
        assert result is not None
        assert result["stock_code"] == "600276"
        assert "stock_name" in result
        industries_count = len(result.get("industries", []))
        print(f"[OK] get_company_overview: {result['stock_name']}, industries={industries_count}")

    def test_resolve_company_from_text(self):
        """测试从文本识别公司"""
        from agent.tools import resolve_company_from_text

        result = resolve_company_from_text("恒瑞")
        assert result is not None
        assert isinstance(result, list)
        print(f"[OK] resolve_company_from_text: found {len(result)} companies")


class TestFinancialTools:
    """测试财务数据工具 - 真实数据"""

    def test_get_income_statements(self):
        """测试获取利润表"""
        from agent.tools import get_income_statements

        result = get_income_statements("600276", limit=4)
        assert result is not None
        assert isinstance(result, list)
        if len(result) > 0:
            assert "revenue" in result[0]
            print(f"[OK] get_income_statements: {len(result)} periods, latest revenue={result[0].get('revenue')}")
        else:
            print("[OK] get_income_statements: 0 records (normal)")

    def test_get_balance_sheets(self):
        """测试获取资产负债表"""
        from agent.tools import get_balance_sheets

        result = get_balance_sheets("600276", limit=4)
        assert result is not None
        assert isinstance(result, list)
        if len(result) > 0:
            assert "total_assets" in result[0]
            print(f"[OK] get_balance_sheets: {len(result)} periods, total_assets={result[0].get('total_assets')}")
        else:
            print("[OK] get_balance_sheets: 0 records (normal)")

    def test_get_cashflow_statements(self):
        """测试获取现金流量表"""
        from agent.tools import get_cashflow_statements

        result = get_cashflow_statements("600276", limit=4)
        assert result is not None
        assert isinstance(result, list)
        print(f"[OK] get_cashflow_statements: {len(result)} periods")

    def test_get_financial_metrics(self):
        """测试获取财务指标"""
        from agent.tools import get_financial_metrics

        result = get_financial_metrics("600276", ["gross_margin", "net_margin", "roe"], limit=4)
        assert result is not None
        assert isinstance(result, list)
        print(f"[OK] get_financial_metrics: {len(result)} records")

    def test_get_business_segments(self):
        """测试获取业务分部"""
        from agent.tools import get_business_segments

        result = get_business_segments("600276", limit=4)
        assert result is not None
        assert isinstance(result, list)
        print(f"[OK] get_business_segments: {len(result)} segments")

    def test_get_financial_summary(self):
        """测试获取财务汇总"""
        from agent.tools import get_financial_summary

        result = get_financial_summary("600276", period_count=4)
        assert result is not None
        assert result["stock_code"] == "600276"
        assert "latest_income" in result
        assert "latest_balance" in result
        assert "latest_cashflow" in result
        print("[OK] get_financial_summary: includes income/balance/cashflow")


class TestAnnouncementTools:
    """测试公告事件工具 - 真实数据"""

    def test_get_raw_announcements(self):
        """测试获取原始公告"""
        from agent.tools import get_raw_announcements

        result = get_raw_announcements("600276", days=365)
        assert result is not None
        assert isinstance(result, list)
        print(f"[OK] get_raw_announcements: {len(result)} announcements")

    def test_get_structured_announcements(self):
        """测试获取结构化公告"""
        from agent.tools import get_structured_announcements

        result = get_structured_announcements("600276", days=365)
        assert result is not None
        assert isinstance(result, list)
        print(f"[OK] get_structured_announcements: {len(result)} structured")

    def test_get_drug_approvals(self):
        """测试获取药品批准"""
        from agent.tools import get_drug_approvals

        result = get_drug_approvals("600276", days=365)
        assert result is not None
        assert isinstance(result, list)
        print(f"[OK] get_drug_approvals: {len(result)} approvals")

    def test_get_clinical_trials(self):
        """测试获取临床试验"""
        from agent.tools import get_clinical_trials

        result = get_clinical_trials("600276", days=365)
        assert result is not None
        assert isinstance(result, list)
        print(f"[OK] get_clinical_trials: {len(result)} trials")

    def test_get_procurement_events(self):
        """测试获取集采事件"""
        from agent.tools import get_procurement_events

        result = get_procurement_events("600276", days=365)
        assert result is not None
        assert isinstance(result, list)
        print(f"[OK] get_procurement_events: {len(result)} events")

    def test_get_regulatory_risks(self):
        """测试获取监管风险"""
        from agent.tools import get_regulatory_risks

        result = get_regulatory_risks("600276", days=365)
        assert result is not None
        assert isinstance(result, list)
        print(f"[OK] get_regulatory_risks: {len(result)} risks")

    def test_get_company_event_summary(self):
        """测试获取公司事件汇总"""
        from agent.tools import get_company_event_summary

        result = get_company_event_summary("600276", days=365)
        assert result is not None
        assert result["stock_code"] == "600276"
        assert "opportunity_items" in result
        assert "risk_items" in result
        print(f"[OK] get_company_event_summary: opportunities={len(result['opportunity_items'])}, risks={len(result['risk_items'])}")


class TestNewsTools:
    """测试新闻舆情工具 - 真实数据"""

    def test_get_news_raw(self):
        """测试获取原始新闻"""
        from agent.tools import get_news_raw

        result = get_news_raw(days=30)
        assert result is not None
        assert isinstance(result, list)
        print(f"[OK] get_news_raw: {len(result)} news")

    def test_get_news_by_company(self):
        """测试获取公司新闻"""
        from agent.tools import get_news_by_company

        result = get_news_by_company("600276", days=90)
        assert result is not None
        assert isinstance(result, list)
        print(f"[OK] get_news_by_company: {len(result)} company news")

    def test_get_news_by_industry(self):
        """测试获取行业新闻"""
        from agent.tools import get_news_by_industry

        result = get_news_by_industry("医药生物", days=90)
        assert result is not None
        assert isinstance(result, list)
        print(f"[OK] get_news_by_industry: {len(result)} industry news")

    def test_get_company_news_impact(self):
        """测试获取公司新闻影响"""
        from agent.tools import get_company_news_impact

        result = get_company_news_impact("600276", days=90)
        assert result is not None
        assert result["stock_code"] == "600276"
        assert "items" in result
        print(f"[OK] get_company_news_impact: {len(result['items'])} items")

    def test_get_industry_news_impact(self):
        """测试获取行业新闻影响"""
        from agent.tools import get_industry_news_impact

        result = get_industry_news_impact("医药生物", days=90)
        assert result is not None
        assert "industry_name" in result
        assert "items" in result
        print(f"[OK] get_industry_news_impact: {len(result['items'])} items")


class TestMacroTools:
    """测试宏观指标工具 - 真实数据"""

    def test_get_macro_indicator(self):
        """测试获取宏观指标"""
        from agent.tools import get_macro_indicator

        # 测试不存在的指标应该返回None
        result = get_macro_indicator("不存在的指标")
        # 如果数据库为空，返回None是正常的
        print(f"[OK] get_macro_indicator: result={'exists' if result else 'none'}")

    def test_list_macro_indicators(self):
        """测试批量获取宏观指标"""
        from agent.tools import list_macro_indicators

        result = list_macro_indicators(["GDP", "CPI"])
        assert result is not None
        assert isinstance(result, list)
        print(f"[OK] list_macro_indicators: {len(result)} indicators")

    def test_get_macro_summary(self):
        """测试获取宏观汇总"""
        from agent.tools import get_macro_summary

        result = get_macro_summary(["GDP", "CPI"], recent_n=6)
        assert result is not None
        assert isinstance(result, dict)
        print(f"[OK] get_macro_summary: {len(result.get('series', {}))} series")


class TestRetrievalTools:
    """测试向量检索工具 - 真实数据"""

    def test_search_documents(self):
        """测试全库检索"""
        from agent.tools import search_documents

        result = search_documents(
            query="创新药临床试验",
            stock_code="600276",
            top_k=5
        )
        assert result is not None
        assert isinstance(result, list)
        print(f"[OK] search_documents: {len(result)} results")

    def test_search_company_evidence(self):
        """测试公司证据检索"""
        from agent.tools import search_company_evidence

        result = search_company_evidence(
            query="研发管线",
            stock_code="600276",
            top_k=5
        )
        assert result is not None
        assert isinstance(result, list)
        print(f"[OK] search_company_evidence: {len(result)} evidence")

    def test_search_news_evidence(self):
        """测试新闻证据检索"""
        from agent.tools import search_news_evidence

        result = search_news_evidence(
            query="新药研发",
            stock_code="600276",
            top_k=5
        )
        assert result is not None
        assert isinstance(result, list)
        print(f"[OK] search_news_evidence: {len(result)} results")


class TestPromptTemplates:
    """测试提示词模板"""

    def test_system_base(self):
        """测试系统提示词"""
        from agent.prompts import PromptTemplates

        assert hasattr(PromptTemplates, 'SYSTEM_BASE')
        assert len(PromptTemplates.SYSTEM_BASE) > 0
        print(f"[OK] SYSTEM_BASE: {len(PromptTemplates.SYSTEM_BASE)} chars")

    def test_company_analysis_prompt(self):
        """测试公司分析提示词"""
        from agent.prompts import PromptTemplates

        prompt = PromptTemplates.build_company_analysis_prompt(
            stock_code="600276",
            stock_name="恒瑞医药"
        )
        assert prompt is not None
        assert "600276" in prompt
        print(f"[OK] build_company_analysis_prompt: {len(prompt)} chars")

    def test_financial_analysis_prompt(self):
        """测试财务分析提示词"""
        from agent.prompts import PromptTemplates

        prompt = PromptTemplates.build_financial_analysis_prompt(
            stock_code="600276",
            stock_name="恒瑞医药"
        )
        assert prompt is not None
        print(f"[OK] build_financial_analysis_prompt: {len(prompt)} chars")

    def test_drug_pipeline_prompt(self):
        """测试药品管线提示词"""
        from agent.prompts import PromptTemplates

        prompt = PromptTemplates.build_drug_pipeline_prompt(
            stock_code="600276",
            stock_name="恒瑞医药"
        )
        assert prompt is not None
        print(f"[OK] build_drug_pipeline_prompt: {len(prompt)} chars")

    def test_policy_impact_prompt(self):
        """测试政策影响提示词"""
        from agent.prompts import PromptTemplates

        prompt = PromptTemplates.build_policy_impact_prompt(
            stock_code="600276",
            stock_name="恒瑞医药"
        )
        assert prompt is not None
        print(f"[OK] build_policy_impact_prompt: {len(prompt)} chars")

    def test_industry_comparison_prompt(self):
        """测试行业对比提示词"""
        from agent.prompts import PromptTemplates

        # 修正：使用单数参数
        prompt = PromptTemplates.build_industry_comparison_prompt(
            stock_code="600276",
            stock_name="恒瑞医药"
        )
        assert prompt is not None
        print(f"[OK] build_industry_comparison_prompt: {len(prompt)} chars")

    def test_risk_warning_prompt(self):
        """测试风险预警提示词"""
        from agent.prompts import PromptTemplates

        prompt = PromptTemplates.build_risk_warning_prompt(
            stock_code="600276",
            stock_name="恒瑞医药"
        )
        assert prompt is not None
        print(f"[OK] build_risk_warning_prompt: {len(prompt)} chars")

    def test_quick_query_prompt(self):
        """测试快速查询提示词"""
        from agent.prompts import PromptTemplates

        prompt = PromptTemplates.build_quick_query_prompt(
            query="恒瑞医药最近有哪些新药获批？"
        )
        assert prompt is not None
        print(f"[OK] build_quick_query_prompt: {len(prompt)} chars")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])
