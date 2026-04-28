from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from app.router.schemas.chat import ChatRequest, ChatResponse
from agent.integration.agent import LangChainAgentStub
from agent.integration.mode_resolver import is_valid_mode, normalize_mode, resolve_mode
from agent.integration.state import AgentState


class TestChatSchemas:
    def test_chat_request_defaults(self):
        req = ChatRequest(message="你好")

        assert req.message == "你好"
        assert req.history == []
        assert req.targets == []
        assert req.selected_mode is None
        assert req.frontend_context is None
        assert req.followup_from is None
        assert req.preference_hint is None

    def test_chat_request_accepts_new_agent_fields(self):
        req = ChatRequest(
            message="分析恒瑞医药集采影响",
            selected_mode="policy_procurement",
            frontend_context={"page": "chat"},
            followup_from=None,
            preference_hint={"output": "chart_first"},
        )

        assert req.selected_mode == "policy_procurement"
        assert req.frontend_context == {"page": "chat"}
        assert req.preference_hint == {"output": "chart_first"}

    def test_chat_response_defaults(self):
        res = ChatResponse(answer="测试回答")

        assert res.answer == "测试回答"
        assert res.key_points == []
        assert res.key_metrics == []
        assert res.chart_payload == []
        assert res.evidence_list == []
        assert res.follow_up_questions == []
        assert res.warnings == []


class TestAgentState:
    def test_agent_state_defaults_and_result_projection(self):
        state = AgentState(user_question="你好")

        assert state.history == []
        assert state.targets == []
        assert state.tool_plan == []
        assert state.tool_results == []
        assert state.key_metrics == []
        assert state.chart_payload == []
        assert state.evidence_list == []
        assert state.follow_up_questions == []
        assert state.warnings == []

        state.framework = "kimi"
        state.agent_mode = "kimi-k2.5"
        state.resolved_mode = "quick_query"
        state.add_warning("数据缺失", "缺少财务数据")

        result = state.to_agent_result()
        assert result["answer"] == ""
        assert result["framework"] == "kimi"
        assert result["agent_mode"] == "kimi-k2.5"
        assert result["selected_mode"] == "quick_query"
        assert result["warnings"][0]["type"] == "数据缺失"

    def test_agent_state_warning_detail_is_preserved(self):
        state = AgentState(user_question="你好")
        state.add_warning("warn_type", "warn_message", {"a": 1})

        result = state.to_agent_result()
        assert isinstance(result["warnings"], list)
        assert result["warnings"][0]["type"] == "warn_type"
        assert result["warnings"][0]["message"] == "warn_message"
        assert result["warnings"][0]["detail"] == {"a": 1}


class TestModeResolver:
    def test_resolve_mode_cases(self):
        cases = [
            ("恒瑞医药集采影响大吗", None, "policy_procurement"),
            ("它的管线怎么样", None, "pipeline_analysis"),
            ("分析一下营收和净利润", None, "financial_analysis"),
            ("有没有处罚和负面新闻", None, "risk_warning"),
            ("和同行相比怎么样", None, "industry_compare"),
            ("画个趋势图", None, "chart_analysis"),
            ("生成一份分析报告", None, "report_generation"),
            ("公司基本面怎么样", None, "company_analysis"),
            ("你好", None, "quick_query"),
            ("你好", "policy_procurement", "policy_procurement"),
            ("你好", "政策/集采", "policy_procurement"),
            ("分析营收", "pipeline_analysis", "pipeline_analysis"),
            ("分析营收", "bad_mode", "financial_analysis"),
            ("roe怎么样", None, "financial_analysis"),
            ("ind进展如何", None, "pipeline_analysis"),
            ("nda进展如何", None, "pipeline_analysis"),
            ("bla获批了吗", None, "pipeline_analysis"),
            ("drg控费影响", None, "policy_procurement"),
            ("dip支付改革影响", None, "policy_procurement"),
        ]

        for question, selected_mode, expected in cases:
            actual = resolve_mode(question, selected_mode=selected_mode)
            assert actual == expected, (question, selected_mode, expected, actual)

    def test_mode_normalization_and_validation(self):
        assert normalize_mode(None) is None
        assert normalize_mode("") is None
        assert normalize_mode("政策集采") == "policy_procurement"
        assert normalize_mode("bad_mode") is None
        assert is_valid_mode("quick_query") is True
        assert is_valid_mode("bad_mode") is False


class TestLangChainAgentStub:
    def test_agent_run_returns_contract_fields(self):
        fake_result = {
            "answer": "这是本地回退结果",
            "selected_mode": "policy_procurement",
        }

        with patch("agent.integration.agent.GLMMinimalAgent") as agent_cls:
            agent_cls.return_value.run.return_value = fake_result
            agent = LangChainAgentStub()
            result = agent.run(
                "恒瑞医药集采影响大吗",
                history=[],
                targets=[],
                current_stock_code=None,
                user_id=1,
                session_id=1,
                selected_mode="policy_procurement",
                frontend_context={"page": "chat"},
                followup_from=None,
                preference_hint={"output": "chart_first"},
            )

        assert "answer" in result
        assert "framework" in result
        assert "agent_mode" in result
        assert "selected_mode" in result
        assert result["selected_mode"] == "policy_procurement"
        assert result["agent_mode"] != "policy_procurement"
        assert result["framework"] == "kimi"
        assert result["agent_mode"] == "kimi-k2.5"

    def test_agent_run_uses_local_fallback_when_llm_not_configured(self):
        class FakeCompanyService:
            def resolve_company(self, target):
                return SimpleNamespace(
                    success=True,
                    data=[{
                        "stock_code": "600276",
                        "stock_name": "恒瑞医药",
                        "industry_level1": "医药生物",
                        "industry_level2": "创新药",
                    }],
                )

            def get_company_basic_info(self, stock_code):
                return SimpleNamespace(success=False, data=None)

        class FakeRetrievalService:
            def search_announcements(self, request):
                return SimpleNamespace(success=True, data={"items": []})

            def search_financial_notes(self, request):
                return SimpleNamespace(success=True, data={"items": []})

            def search_news(self, request):
                return SimpleNamespace(success=True, data={"items": []})

        class FakeCacheService:
            def get_query_cache(self, request):
                return SimpleNamespace(success=True, data=None)

            def set_query_cache(self, request):
                return SimpleNamespace(success=True, data={})

        class FakeContainer:
            def __init__(self):
                self.company = FakeCompanyService()
                self.retrieval = FakeRetrievalService()
                self.cache = FakeCacheService()
                self.ctx = SimpleNamespace(session=self._session)

            @contextmanager
            def _session(self):
                yield None

        class FakeDimension:
            def __init__(self, name, score, comment):
                self.name = name
                self.score = score
                self.comment = comment

        class FakeAnalysisResult:
            stock_code = "600276"
            stock_name = "恒瑞医药"
            year = 2024
            total_score = 88
            level = "A"
            strengths = ["研发投入高"]
            weaknesses = ["集采压力"]
            suggestion = "继续跟踪政策变化"
            dimensions = [FakeDimension("成长", 90, "表现良好")]

        class FakeAnalysisService:
            def diagnose(self, db, stock_code, year):
                return FakeAnalysisResult()

            def get_metric_trend(self, db, stock_code, metric_name):
                return {"trend": [{"period": "2023", "value": 1}, {"period": "2024", "value": 2}]}

        with patch("agent.integration.glm_agent.ServiceContainer.build_default", return_value=FakeContainer()), \
             patch("app.router.analysis_service.AnalysisService", return_value=FakeAnalysisService()), \
             patch("agent.integration.glm_agent.KimiClient") as kimi_cls, \
             patch("agent.integration.glm_agent.get_store") as get_store_mock:
            kimi_cls.return_value.is_configured.return_value = False
            get_store_mock.return_value.search.return_value = []

            agent = LangChainAgentStub()
            result = agent.run(
                "恒瑞医药集采影响大吗",
                history=[],
                targets=[],
                current_stock_code=None,
                user_id=1,
                session_id=1,
                selected_mode="policy_procurement",
                frontend_context={"page": "chat"},
                followup_from=None,
                preference_hint={"output": "chart_first"},
            )

        assert result["selected_mode"] == "policy_procurement"
        assert result["framework"] == "kimi"
        assert result["agent_mode"] == "kimi-config-missing"
        assert isinstance(result["answer"], str)
        assert result["answer"]
