"""Agent工具函数测试 - 使用mock数据"""

import pytest
import sys
from pathlib import Path

# 确保可以导入项目模块
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestCompanyTools:
    """测试公司信息工具"""

    def test_get_company_basic_info(self, services, monkeypatch):
        """测试获取公司基本信息"""
        # Mock ServiceContainer
        from agent.tools import company_tools

        class MockContainer:
            def __init__(self):
                self.company = services["company"]

        def mock_build_default():
            return MockContainer()

        monkeypatch.setattr("agent.tools.company_tools.ServiceContainer.build_default", mock_build_default)

        # 测试
        from agent.tools import get_company_basic_info

        result = get_company_basic_info("600276")

        assert result is not None
        assert result["stock_code"] == "600276"
        assert result["stock_name"] == "恒瑞医药"
        assert result["industry_level1"] == "医药生物"
        assert result["industry_level2"] == "创新药"
        print(f"✓ get_company_basic_info: {result['stock_name']}")

    def test_get_company_profile(self, services, monkeypatch):
        """测试获取公司资料"""
        from agent.tools import company_tools

        class MockContainer:
            def __init__(self):
                self.company = services["company"]

        def mock_build_default():
            return MockContainer()

        monkeypatch.setattr("agent.tools.company_tools.ServiceContainer.build_default", mock_build_default)

        from agent.tools import get_company_profile

        result = get_company_profile("600276")

        assert result is not None
        assert result["stock_code"] == "600276"
        assert "business_summary" in result
        print(f"✓ get_company_profile: {result['business_summary'][:30]}...")

    def test_get_company_overview(self, services, monkeypatch):
        """测试获取公司完整概览"""
        from agent.tools import company_tools

        class MockContainer:
            def __init__(self):
                self.company = services["company"]

        def mock_build_default():
            return MockContainer()

        monkeypatch.setattr("agent.tools.company_tools.ServiceContainer.build_default", mock_build_default)

        from agent.tools import get_company_overview

        result = get_company_overview("600276")

        assert result is not None
        assert result["stock_code"] == "600276"
        assert result["stock_name"] == "恒瑞医药"
        assert "profile" in result
        assert "industries" in result
        print(f"✓ get_company_overview: {result['stock_name']}, 行业数: {len(result['industries'])}")

    def test_resolve_company_from_text(self, services, monkeypatch):
        """测试从文本识别公司"""
        from agent.tools import company_tools

        class MockContainer:
            def __init__(self):
                self.company = services["company"]

        def mock_build_default():
            return MockContainer()

        monkeypatch.setattr("agent.tools.company_tools.ServiceContainer.build_default", mock_build_default)

        from agent.tools import resolve_company_from_text

        result = resolve_company_from_text("恒瑞")

        assert result is not None
        assert len(result) > 0
        assert result[0]["stock_code"] == "600276"
        print(f"✓ resolve_company_from_text: 识别到 {len(result)} 家公司")


class TestFinancialTools:
    """测试财务数据工具"""

    def test_get_income_statements(self, services, monkeypatch):
        """测试获取利润表"""
        from agent.tools import financial_tools

        class MockContainer:
            def __init__(self):
                self.financial = services["financial"]

        def mock_build_default():
            return MockContainer()

        monkeypatch.setattr("agent.tools.financial_tools.ServiceContainer.build_default", mock_build_default)

        from agent.tools import get_income_statements

        result = get_income_statements("600276", limit=4)

        assert result is not None
        assert len(result) > 0
        assert result[0]["stock_code"] == "600276"
        assert "revenue" in result[0]
        assert "net_profit" in result[0]
        print(f"✓ get_income_statements: {len(result)}期数据, 最新收入={result[0]['revenue']}")

    def test_get_balance_sheets(self, services, monkeypatch):
        """测试获取资产负债表"""
        from agent.tools import financial_tools

        class MockContainer:
            def __init__(self):
                self.financial = services["financial"]

        def mock_build_default():
            return MockContainer()

        monkeypatch.setattr("agent.tools.financial_tools.ServiceContainer.build_default", mock_build_default)

        from agent.tools import get_balance_sheets

        result = get_balance_sheets("600276", limit=4)

        assert result is not None
        assert len(result) > 0
        assert "total_assets" in result[0]
        assert "total_liabilities" in result[0]
        print(f"✓ get_balance_sheets: {len(result)}期数据, 总资产={result[0]['total_assets']}")

    def test_get_financial_summary(self, services, monkeypatch):
        """测试获取财务汇总"""
        from agent.tools import financial_tools

        class MockContainer:
            def __init__(self):
                self.financial = services["financial"]

        def mock_build_default():
            return MockContainer()

        monkeypatch.setattr("agent.tools.financial_tools.ServiceContainer.build_default", mock_build_default)

        from agent.tools import get_financial_summary

        result = get_financial_summary("600276", period_count=4)

        assert result is not None
        assert result["stock_code"] == "600276"
        assert "latest_income" in result
        assert "latest_balance" in result
        assert "latest_cashflow" in result
        print(f"✓ get_financial_summary: 包含利润表、资产负债表、现金流量表")


class TestAnnouncementTools:
    """测试公告事件工具"""

    def test_get_raw_announcements(self, services, monkeypatch):
        """测试获取原始公告"""
        from agent.tools import announcement_tools

        class MockContainer:
            def __init__(self):
                self.announcement = services["announcement"]

        def mock_build_default():
            return MockContainer()

        monkeypatch.setattr("agent.tools.announcement_tools.ServiceContainer.build_default", mock_build_default)

        from agent.tools import get_raw_announcements

        result = get_raw_announcements("600276", days=365)

        assert result is not None
        assert isinstance(result, list)
        if len(result) > 0:
            assert "title" in result[0]
            print(f"✓ get_raw_announcements: {len(result)}条公告")
        else:
            print(f"✓ get_raw_announcements: 0条公告（正常）")

    def test_get_structured_announcements(self, services, monkeypatch):
        """测试获取结构化公告"""
        from agent.tools import announcement_tools

        class MockContainer:
            def __init__(self):
                self.announcement = services["announcement"]

        def mock_build_default():
            return MockContainer()

        monkeypatch.setattr("agent.tools.announcement_tools.ServiceContainer.build_default", mock_build_default)

        from agent.tools import get_structured_announcements

        result = get_structured_announcements("600276", days=365)

        assert result is not None
        assert isinstance(result, list)
        print(f"✓ get_structured_announcements: {len(result)}条结构化公告")

    def test_get_drug_approvals(self, services, monkeypatch):
        """测试获取药品批准"""
        from agent.tools import announcement_tools

        class MockContainer:
            def __init__(self):
                self.announcement = services["announcement"]

        def mock_build_default():
            return MockContainer()

        monkeypatch.setattr("agent.tools.announcement_tools.ServiceContainer.build_default", mock_build_default)

        from agent.tools import get_drug_approvals

        result = get_drug_approvals("600276", days=365)

        assert result is not None
        assert isinstance(result, list)
        if len(result) > 0:
            assert "drug_name" in result[0]
            print(f"✓ get_drug_approvals: {len(result)}个药品批准, 首个={result[0]['drug_name']}")
        else:
            print(f"✓ get_drug_approvals: 0个药品批准（正常）")


class TestNewsTools:
    """测试新闻舆情工具"""

    def test_get_news_raw(self, services, monkeypatch):
        """测试获取原始新闻"""
        from agent.tools import news_tools

        class MockContainer:
            def __init__(self):
                self.news = services["news"]

        def mock_build_default():
            return MockContainer()

        monkeypatch.setattr("agent.tools.news_tools.ServiceContainer.build_default", mock_build_default)

        from agent.tools import get_news_raw

        result = get_news_raw(days=30)

        assert result is not None
        assert isinstance(result, list)
        if len(result) > 0:
            assert "title" in result[0]
            print(f"✓ get_news_raw: {len(result)}条新闻")
        else:
            print(f"✓ get_news_raw: 0条新闻（正常）")

    def test_get_news_by_company(self, services, monkeypatch):
        """测试获取公司新闻"""
        from agent.tools import news_tools

        class MockContainer:
            def __init__(self):
                self.news = services["news"]

        def mock_build_default():
            return MockContainer()

        monkeypatch.setattr("agent.tools.news_tools.ServiceContainer.build_default", mock_build_default)

        from agent.tools import get_news_by_company

        result = get_news_by_company("600276", days=90)

        assert result is not None
        assert isinstance(result, list)
        print(f"✓ get_news_by_company: {len(result)}条公司新闻")

    def test_get_company_news_impact(self, services, monkeypatch):
        """测试获取公司新闻影响"""
        from agent.tools import news_tools

        class MockContainer:
            def __init__(self):
                self.news = services["news"]

        def mock_build_default():
            return MockContainer()

        monkeypatch.setattr("agent.tools.news_tools.ServiceContainer.build_default", mock_build_default)

        from agent.tools import get_company_news_impact

        result = get_company_news_impact("600276", days=90)

        assert result is not None
        assert result["stock_code"] == "600276"
        assert "items" in result
        assert "direction_counts" in result
        print(f"✓ get_company_news_impact: {len(result['items'])}条新闻, 方向统计={result['direction_counts']}")


class TestMacroTools:
    """测试宏观指标工具"""

    def test_get_macro_indicator(self, services, monkeypatch):
        """测试获取宏观指标"""
        from agent.tools import macro_tools

        class MockContainer:
            def __init__(self):
                self.macro = services["macro"]

        def mock_build_default():
            return MockContainer()

        monkeypatch.setattr("agent.tools.macro_tools.ServiceContainer.build_default", mock_build_default)

        from agent.tools import get_macro_indicator

        result = get_macro_indicator("医药制造业增加值")

        assert result is not None
        assert result["indicator_name"] == "医药制造业增加值"
        assert "value" in result
        print(f"✓ get_macro_indicator: {result['indicator_name']}={result['value']}{result.get('unit', '')}")

    def test_list_macro_indicators(self, services, monkeypatch):
        """测试批量获取宏观指标"""
        from agent.tools import macro_tools

        class MockContainer:
            def __init__(self):
                self.macro = services["macro"]

        def mock_build_default():
            return MockContainer()

        monkeypatch.setattr("agent.tools.macro_tools.ServiceContainer.build_default", mock_build_default)

        from agent.tools import list_macro_indicators

        result = list_macro_indicators(["医药制造业增加值"])

        assert result is not None
        assert isinstance(result, list)
        print(f"✓ list_macro_indicators: {len(result)}个指标")


class TestRetrievalTools:
    """测试向量检索工具"""

    def test_search_documents(self, services, monkeypatch):
        """测试全库检索"""
        from agent.tools import retrieval_tools

        class MockContainer:
            def __init__(self):
                self.retrieval = services["retrieval"]

        def mock_build_default():
            return MockContainer()

        monkeypatch.setattr("agent.tools.retrieval_tools.ServiceContainer.build_default", mock_build_default)

        from agent.tools import search_documents

        result = search_documents(
            query="创新药临床试验",
            stock_code="600276",
            top_k=5
        )

        assert result is not None
        assert isinstance(result, list)
        if len(result) > 0:
            # doc_type 在 metadata 字段内
            assert "metadata" in result[0] or "doc_type" in result[0]
            print(f"OK search_documents: {len(result)}条结果")
        else:
            print(f"✓ search_documents: 0条结果（正常）")

    def test_search_company_evidence(self, services, monkeypatch):
        """测试公司证据检索"""
        from agent.tools import retrieval_tools

        class MockContainer:
            def __init__(self):
                self.retrieval = services["retrieval"]

        def mock_build_default():
            return MockContainer()

        monkeypatch.setattr("agent.tools.retrieval_tools.ServiceContainer.build_default", mock_build_default)

        from agent.tools import search_company_evidence

        result = search_company_evidence(
            query="研发管线",
            stock_code="600276",
            top_k=5
        )

        assert result is not None
        assert isinstance(result, list)
        print(f"✓ search_company_evidence: {len(result)}条证据")


class TestPromptTemplates:
    """测试提示词模板"""

    def test_system_base(self):
        """测试系统提示词"""
        from agent.prompts import PromptTemplates

        assert hasattr(PromptTemplates, 'SYSTEM_BASE')
        assert len(PromptTemplates.SYSTEM_BASE) > 0
        assert "智策系统" in PromptTemplates.SYSTEM_BASE
        print(f"✓ SYSTEM_BASE: {len(PromptTemplates.SYSTEM_BASE)}字符")

    def test_company_analysis_prompt(self):
        """测试公司分析提示词"""
        from agent.prompts import PromptTemplates

        prompt = PromptTemplates.build_company_analysis_prompt(
            stock_code="600276",
            stock_name="恒瑞医药"
        )

        assert prompt is not None
        assert "600276" in prompt
        assert "恒瑞医药" in prompt
        assert "公司概况" in prompt
        assert "财务健康度" in prompt
        print(f"✓ build_company_analysis_prompt: {len(prompt)}字符")

    def test_financial_analysis_prompt(self):
        """测试财务分析提示词"""
        from agent.prompts import PromptTemplates

        prompt = PromptTemplates.build_financial_analysis_prompt(
            stock_code="600276",
            stock_name="恒瑞医药"
        )

        assert prompt is not None
        assert "盈利能力" in prompt
        assert "现金流" in prompt
        print(f"✓ build_financial_analysis_prompt: {len(prompt)}字符")

    def test_drug_pipeline_prompt(self):
        """测试药品管线提示词"""
        from agent.prompts import PromptTemplates

        prompt = PromptTemplates.build_drug_pipeline_prompt(
            stock_code="600276",
            stock_name="恒瑞医药"
        )

        assert prompt is not None
        assert "药品管线" in prompt
        assert "在研管线" in prompt
        print(f"✓ build_drug_pipeline_prompt: {len(prompt)}字符")

    def test_quick_query_prompt(self):
        """测试快速查询提示词"""
        from agent.prompts import PromptTemplates

        prompt = PromptTemplates.build_quick_query_prompt(
            query="恒瑞医药最近有哪些新药获批？"
        )

        assert prompt is not None
        assert "恒瑞医药最近有哪些新药获批？" in prompt
        print(f"✓ build_quick_query_prompt: {len(prompt)}字符")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
