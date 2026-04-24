"""M1/M2 医药能力模块测试。

覆盖范围：
  M1 - 骨架可导入、数据结构完整、空数据路径不崩溃
  M2 - 评分逻辑正确、数据库驱动的 MedicalAnalyzer 端到端
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from decimal import Decimal
from datetime import date

# ── M1 导入测试 ──────────────────────────────────────────────────────────────

class TestM1Imports:
    """M1：所有新增模块可正常导入，公开接口存在。"""

    def test_scoring_tools_importable(self):
        from agent.tools.scoring_tools import PharmaScorer, PharmaScoreResult, DimensionScore, SCORING_DIMENSIONS
        assert PharmaScorer is not None
        assert PharmaScoreResult is not None
        assert DimensionScore is not None

    def test_scoring_dimensions_count(self):
        from agent.tools.scoring_tools import SCORING_DIMENSIONS
        assert len(SCORING_DIMENSIONS) == 10

    def test_scoring_dimensions_names(self):
        from agent.tools.scoring_tools import SCORING_DIMENSIONS
        expected = {"财务质量", "研发实力", "管线价值", "审批进展", "临床风险",
                    "回款风险", "医保管控风险", "商业化能力", "合规风险", "舆情风险"}
        assert set(SCORING_DIMENSIONS) == expected

    def test_chart_tools_importable(self):
        from agent.tools.chart_tools import PharmaChartBuilder, ChartConfig
        assert PharmaChartBuilder is not None
        assert ChartConfig is not None

    def test_evidence_tools_importable(self):
        from agent.tools.evidence_tools import PharmaEvidenceCollector, EvidenceBundle, EvidenceItem
        assert PharmaEvidenceCollector is not None
        assert EvidenceBundle is not None
        assert EvidenceItem is not None

    def test_pharma_decision_tools_importable(self):
        from agent.tools.pharma_decision_tools import PharmaDecisionTool, PharmaDecisionResult
        assert PharmaDecisionTool is not None
        assert PharmaDecisionResult is not None

    def test_medical_analyzer_importable(self):
        from agent.integration.medical_analyzer import MedicalAnalyzer, MedicalAnalysisResult
        assert MedicalAnalyzer is not None
        assert MedicalAnalysisResult is not None


# ── M1 空数据路径 ─────────────────────────────────────────────────────────────

class TestM1EmptyData:
    """M1：空数据输入不崩溃，返回合理默认值。"""

    def test_scorer_empty_returns_result(self):
        from agent.tools.scoring_tools import PharmaScorer
        result = PharmaScorer().score("600276", "恒瑞医药", 2024)
        assert result.stock_code == "600276"
        assert result.stock_name == "恒瑞医药"
        assert result.year == 2024
        assert isinstance(result.total_score, float)
        assert result.level in ("优秀", "良好", "一般", "较差", "差")

    def test_scorer_empty_has_all_dimensions(self):
        from agent.tools.scoring_tools import PharmaScorer, SCORING_DIMENSIONS
        result = PharmaScorer().score("600276", "恒瑞医药", 2024)
        assert len(result.dimensions) == 10
        dim_names = {d.name for d in result.dimensions}
        assert dim_names == set(SCORING_DIMENSIONS)

    def test_scorer_empty_scores_in_range(self):
        from agent.tools.scoring_tools import PharmaScorer
        result = PharmaScorer().score("600276", "恒瑞医药", 2024)
        for d in result.dimensions:
            assert 0 <= d.score <= 100, f"{d.name} score {d.score} out of range"
        assert 0 <= result.total_score <= 100

    def test_scorer_empty_weights_sum(self):
        from agent.tools.scoring_tools import PharmaScorer
        result = PharmaScorer().score("600276", "恒瑞医药", 2024)
        total_weight = sum(d.weight for d in result.dimensions)
        assert abs(total_weight - 1.0) < 1e-6

    def test_scorer_empty_has_missing_flags(self):
        from agent.tools.scoring_tools import PharmaScorer
        result = PharmaScorer().score("600276", "恒瑞医药", 2024)
        assert isinstance(result.data_missing, list)
        assert len(result.data_missing) > 0

    def test_decision_tool_empty_no_crash(self):
        from agent.tools.pharma_decision_tools import PharmaDecisionTool
        result = PharmaDecisionTool().analyze(
            stock_code="600276", stock_name="恒瑞医药", year=2024
        )
        assert result.stock_code == "600276"
        assert result.score_result is not None
        assert isinstance(result.warnings, list)

    def test_evidence_collector_empty(self):
        from agent.tools.evidence_tools import PharmaEvidenceCollector
        bundle = PharmaEvidenceCollector().collect(
            query="研发管线", stock_code="600276", stock_name="恒瑞医药"
        )
        assert bundle.stock_code == "600276"
        assert isinstance(bundle.items, list)
        assert isinstance(bundle.missing_types, list)

    def test_chart_builder_radar_no_crash(self):
        from agent.tools.chart_tools import PharmaChartBuilder
        cfg = PharmaChartBuilder().build_score_radar([], "恒瑞医药")
        assert cfg.chart_type == "radar"
        assert "恒瑞医药" in cfg.title

    def test_chart_builder_trend_no_crash(self):
        from agent.tools.chart_tools import PharmaChartBuilder
        cfg = PharmaChartBuilder().build_financial_trend("营业总收入", [], "恒瑞医药")
        assert cfg.chart_type == "line"

    def test_chart_builder_pipeline_no_crash(self):
        from agent.tools.chart_tools import PharmaChartBuilder
        cfg = PharmaChartBuilder().build_pipeline_bar([], "恒瑞医药")
        assert cfg.chart_type == "bar"


# ── M2 评分逻辑 ───────────────────────────────────────────────────────────────

class TestM2ScoringLogic:
    """M2：评分函数对具体数值产生正确的方向性结果。"""

    @pytest.fixture
    def scorer(self):
        from agent.tools.scoring_tools import PharmaScorer
        return PharmaScorer()

    @pytest.fixture
    def good_fd(self):
        return {
            "gross_margin": 72.0,
            "net_margin": 20.0,
            "roe": 18.0,
            "debt_ratio": 25.0,
            "rd_ratio": 16.0,
            "revenue": 2.5e10,
            "revenue_growth": 20.0,
            "ar_ratio": 0.15,
            "cashflow_quality": 1.2,
            "operating_cashflow": 3e9,
            "selling_ratio": 0.18,
            "segment_count": 4,
        }

    @pytest.fixture
    def bad_fd(self):
        return {
            "gross_margin": 15.0,
            "net_margin": 2.0,
            "roe": 3.0,
            "debt_ratio": 70.0,
            "rd_ratio": 2.0,
            "revenue": 1e8,
            "revenue_growth": -15.0,
            "ar_ratio": 0.55,
            "cashflow_quality": 0.3,
            "operating_cashflow": -1e8,
            "selling_ratio": 0.45,
        }

    @pytest.fixture
    def good_pd(self):
        return {
            "pipeline_total": 20,
            "pipeline_phase3": 5,
            "innovative_drug_ratio": 0.5,
            "recent_approvals": 3,
            "innovative_approvals": 2,
            "pending_review_count": 4,
            "trial_failures": 0,
            "phase3_failures": 0,
            "active_trials": 10,
            "avg_price_cut_ratio": 0.2,
            "procurement_wins": 4,
            "procurement_failures": 0,
            "regulatory_total": 0,
            "regulatory_high_risk": 0,
            "sentiment_score": 0.5,
            "negative_news_ratio": 0.1,
            "high_impact_negative": 0,
        }

    @pytest.fixture
    def bad_pd(self):
        return {
            "pipeline_total": 2,
            "pipeline_phase3": 0,
            "innovative_drug_ratio": 0.05,
            "recent_approvals": 0,
            "innovative_approvals": 0,
            "trial_failures": 4,
            "phase3_failures": 2,
            "active_trials": 1,
            "avg_price_cut_ratio": 0.85,
            "procurement_wins": 0,
            "procurement_failures": 3,
            "regulatory_total": 5,
            "regulatory_high_risk": 2,
            "sentiment_score": -0.6,
            "negative_news_ratio": 0.7,
            "high_impact_negative": 3,
        }

    def test_good_data_scores_higher_than_bad(self, scorer, good_fd, bad_fd, good_pd, bad_pd):
        good = scorer.score("600276", "恒瑞医药", 2024, financial_data=good_fd, pipeline_data=good_pd)
        bad = scorer.score("600276", "恒瑞医药", 2024, financial_data=bad_fd, pipeline_data=bad_pd)
        assert good.total_score > bad.total_score, (
            f"good={good.total_score} should > bad={bad.total_score}"
        )

    def test_good_data_level(self, scorer, good_fd, good_pd):
        result = scorer.score("600276", "恒瑞医药", 2024, financial_data=good_fd, pipeline_data=good_pd)
        assert result.level in ("优秀", "良好"), f"expected 优秀/良好, got {result.level}"

    def test_bad_data_level(self, scorer, bad_fd, bad_pd):
        result = scorer.score("600276", "恒瑞医药", 2024, financial_data=bad_fd, pipeline_data=bad_pd)
        assert result.level in ("较差", "差", "一般"), f"expected 较差/差/一般, got {result.level}"

    def test_no_missing_when_full_data(self, scorer, good_fd, good_pd):
        result = scorer.score("600276", "恒瑞医药", 2024, financial_data=good_fd, pipeline_data=good_pd)
        assert result.data_missing == []

    def test_financial_quality_higher_gross_margin_scores_higher(self, scorer):
        high = scorer.score("X", "X", 2024, financial_data={"gross_margin": 70.0})
        low = scorer.score("X", "X", 2024, financial_data={"gross_margin": 15.0})
        high_dim = next(d for d in high.dimensions if d.name == "财务质量")
        low_dim = next(d for d in low.dimensions if d.name == "财务质量")
        assert high_dim.score > low_dim.score

    def test_rd_strength_higher_ratio_scores_higher(self, scorer):
        high = scorer.score("X", "X", 2024, financial_data={"rd_ratio": 18.0})
        low = scorer.score("X", "X", 2024, financial_data={"rd_ratio": 2.0})
        high_dim = next(d for d in high.dimensions if d.name == "研发实力")
        low_dim = next(d for d in low.dimensions if d.name == "研发实力")
        assert high_dim.score > low_dim.score

    def test_clinical_risk_failures_lower_score(self, scorer):
        safe = scorer.score("X", "X", 2024, pipeline_data={"trial_failures": 0})
        risky = scorer.score("X", "X", 2024, pipeline_data={"trial_failures": 4, "phase3_failures": 2})
        safe_dim = next(d for d in safe.dimensions if d.name == "临床风险")
        risky_dim = next(d for d in risky.dimensions if d.name == "临床风险")
        assert safe_dim.score > risky_dim.score

    def test_compliance_risk_no_events_default_high(self, scorer):
        result = scorer.score("X", "X", 2024, pipeline_data={})
        dim = next(d for d in result.dimensions if d.name == "合规风险")
        assert dim.score >= 70

    def test_sentiment_positive_scores_higher(self, scorer):
        pos = scorer.score("X", "X", 2024, pipeline_data={"sentiment_score": 0.8, "negative_news_ratio": 0.05})
        neg = scorer.score("X", "X", 2024, pipeline_data={"sentiment_score": -0.8, "negative_news_ratio": 0.8})
        pos_dim = next(d for d in pos.dimensions if d.name == "舆情风险")
        neg_dim = next(d for d in neg.dimensions if d.name == "舆情风险")
        assert pos_dim.score > neg_dim.score

    def test_strengths_are_high_scoring_dims(self, scorer, good_fd, good_pd):
        result = scorer.score("600276", "恒瑞医药", 2024, financial_data=good_fd, pipeline_data=good_pd)
        dim_map = {d.name: d.score for d in result.dimensions}
        for name in result.strengths:
            assert dim_map[name] >= 60, f"strength {name} has score {dim_map[name]} < 60"

    def test_weaknesses_are_low_scoring_dims(self, scorer, bad_fd, bad_pd):
        result = scorer.score("600276", "恒瑞医药", 2024, financial_data=bad_fd, pipeline_data=bad_pd)
        dim_map = {d.name: d.score for d in result.dimensions}
        for name in result.weaknesses:
            assert dim_map[name] < 60, f"weakness {name} has score {dim_map[name]} >= 60"

    def test_dimension_comments_non_empty(self, scorer, good_fd, good_pd):
        result = scorer.score("600276", "恒瑞医药", 2024, financial_data=good_fd, pipeline_data=good_pd)
        for d in result.dimensions:
            assert d.comment, f"{d.name} has empty comment"

    def test_total_score_equals_weighted_sum(self, scorer, good_fd, good_pd):
        result = scorer.score("600276", "恒瑞医药", 2024, financial_data=good_fd, pipeline_data=good_pd)
        expected = round(sum(d.score * d.weight for d in result.dimensions), 1)
        assert abs(result.total_score - expected) < 0.05


# ── M2 MedicalAnalyzer 端到端（SQLite in-memory）────────────────────────────

class TestM2MedicalAnalyzer:
    """M2：MedicalAnalyzer 从 SQLite 测试库读取数据，端到端验证。"""

    def test_analyze_returns_result(self, session_factory):
        from agent.integration.medical_analyzer import MedicalAnalyzer
        analyzer = MedicalAnalyzer()
        with session_factory() as db:
            result = analyzer.analyze(db, "600276", "恒瑞医药", 2024)
        assert result.stock_code == "600276"
        assert result.stock_name == "恒瑞医药"
        assert result.year == 2024

    def test_analyze_score_in_range(self, session_factory):
        from agent.integration.medical_analyzer import MedicalAnalyzer
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(db, "600276", "恒瑞医药", 2024)
        assert 0 <= result.total_score <= 100

    def test_analyze_level_valid(self, session_factory):
        from agent.integration.medical_analyzer import MedicalAnalyzer
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(db, "600276", "恒瑞医药", 2024)
        assert result.level in ("优秀", "良好", "一般", "较差", "差")

    def test_analyze_has_ten_dimensions(self, session_factory):
        from agent.integration.medical_analyzer import MedicalAnalyzer
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(db, "600276", "恒瑞医药", 2024)
        assert len(result.dimensions) == 10

    def test_analyze_dimensions_have_required_fields(self, session_factory):
        from agent.integration.medical_analyzer import MedicalAnalyzer
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(db, "600276", "恒瑞医药", 2024)
        for d in result.dimensions:
            assert "name" in d
            assert "score" in d
            assert "weight" in d
            assert "comment" in d

    def test_analyze_suggestion_non_empty(self, session_factory):
        from agent.integration.medical_analyzer import MedicalAnalyzer
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(db, "600276", "恒瑞医药", 2024)
        assert result.suggestion and len(result.suggestion) > 0

    def test_analyze_financial_data_loaded(self, session_factory):
        """conftest 中有 gross_margin=0.80 的 metric，财务质量维度应高于空数据默认分。"""
        from agent.integration.medical_analyzer import MedicalAnalyzer
        from agent.tools.scoring_tools import PharmaScorer
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(db, "600276", "恒瑞医药", 2024)
        empty_result = PharmaScorer().score("600276", "恒瑞医药", 2024)
        db_dim = next(d for d in result.dimensions if d["name"] == "财务质量")
        empty_dim = next(d for d in empty_result.dimensions if d.name == "财务质量")
        assert db_dim["score"] > empty_dim.score, (
            f"DB-driven score {db_dim['score']} should > empty default {empty_dim.score}"
        )

    def test_analyze_pipeline_data_loaded(self, session_factory):
        """conftest 中有 DrugApprovalHot 和 ClinicalTrialEventHot，管线维度应高于空数据默认分。"""
        from agent.integration.medical_analyzer import MedicalAnalyzer
        from agent.tools.scoring_tools import PharmaScorer
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(db, "600276", "恒瑞医药", 2024)
        empty_result = PharmaScorer().score("600276", "恒瑞医药", 2024)
        db_dim = next(d for d in result.dimensions if d["name"] == "管线价值")
        empty_dim = next(d for d in empty_result.dimensions if d.name == "管线价值")
        assert db_dim["score"] > empty_dim.score

    def test_analyze_unknown_company_no_crash(self, session_factory):
        """不存在的股票代码不应抛出异常，应返回默认评分。"""
        from agent.integration.medical_analyzer import MedicalAnalyzer
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(db, "999999", "不存在公司", 2024)
        assert result is not None
        assert 0 <= result.total_score <= 100

    def test_analyze_with_raw_evidence(self, session_factory):
        """传入 raw_evidence 时，evidence 字段应被填充。"""
        from agent.integration.medical_analyzer import MedicalAnalyzer
        raw = [
            {"kind": "announcement", "title": "临床进展", "date": "2024-01-01",
             "source": "SSE", "summary": "III期入组完成"},
        ]
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(
                db, "600276", "恒瑞医药", 2024, raw_evidence=raw
            )
        assert isinstance(result.evidence, list)

    def test_analyze_warnings_is_list(self, session_factory):
        from agent.integration.medical_analyzer import MedicalAnalyzer
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(db, "600276", "恒瑞医药", 2024)
        assert isinstance(result.warnings, list)

    def test_analyze_data_missing_is_list(self, session_factory):
        from agent.integration.medical_analyzer import MedicalAnalyzer
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(db, "600276", "恒瑞医药", 2024)
        assert isinstance(result.data_missing, list)


# ── M3 图表构建 ───────────────────────────────────────────────────────────────

class TestM3ChartBuilder:
    """M3：PharmaChartBuilder 生成结构正确的 ECharts 配置。"""

    @pytest.fixture
    def builder(self):
        from agent.tools.chart_tools import PharmaChartBuilder
        return PharmaChartBuilder()

    @pytest.fixture
    def dims(self):
        return [
            {"name": "财务质量", "score": 75.0, "weight": 0.15},
            {"name": "研发实力", "score": 88.0, "weight": 0.15},
            {"name": "管线价值", "score": 62.0, "weight": 0.15},
        ]

    def test_radar_chart_type(self, builder, dims):
        cfg = builder.build_score_radar(dims, "恒瑞医药")
        assert cfg.chart_type == "radar"

    def test_radar_has_indicator(self, builder, dims):
        cfg = builder.build_score_radar(dims, "恒瑞医药")
        assert "radar" in cfg.extra
        indicators = cfg.extra["radar"]["indicator"]
        assert len(indicators) == 3
        assert indicators[0]["name"] == "财务质量"
        assert indicators[0]["max"] == 100

    def test_radar_series_values_match_scores(self, builder, dims):
        cfg = builder.build_score_radar(dims, "恒瑞医药")
        values = cfg.series[0]["data"][0]["value"]
        assert values == [75.0, 88.0, 62.0]

    def test_radar_empty_dims_no_crash(self, builder):
        cfg = builder.build_score_radar([], "恒瑞医药")
        assert cfg.chart_type == "radar"
        assert "恒瑞医药" in cfg.title

    def test_trend_chart_type(self, builder):
        points = [{"year": 2022, "value": 200.0, "unit": "亿元"},
                  {"year": 2023, "value": 228.0, "unit": "亿元"}]
        cfg = builder.build_financial_trend("营业总收入", points, "恒瑞医药")
        assert cfg.chart_type == "line"

    def test_trend_x_axis_matches_years(self, builder):
        points = [{"year": 2022, "value": 200.0}, {"year": 2023, "value": 228.0}]
        cfg = builder.build_financial_trend("营业总收入", points, "恒瑞医药")
        assert cfg.x_axis == ["2022", "2023"]

    def test_trend_series_data_matches_values(self, builder):
        points = [{"year": 2022, "value": 200.0}, {"year": 2023, "value": 228.0}]
        cfg = builder.build_financial_trend("营业总收入", points, "恒瑞医药")
        assert cfg.series[0]["data"] == [200.0, 228.0]

    def test_trend_empty_points_no_crash(self, builder):
        cfg = builder.build_financial_trend("营业总收入", [], "恒瑞医药")
        assert cfg.chart_type == "line"
        assert cfg.x_axis == []

    def test_pipeline_bar_chart_type(self, builder):
        stages = [{"stage": "III期", "count": 5, "innovative": 3}]
        cfg = builder.build_pipeline_bar(stages, "恒瑞医药")
        assert cfg.chart_type == "bar"

    def test_pipeline_bar_x_axis(self, builder):
        stages = [{"stage": "III期", "count": 5, "innovative": 3},
                  {"stage": "NDA", "count": 2, "innovative": 2}]
        cfg = builder.build_pipeline_bar(stages, "恒瑞医药")
        assert cfg.x_axis == ["III期", "NDA"]

    def test_pipeline_bar_two_series(self, builder):
        stages = [{"stage": "III期", "count": 5, "innovative": 3}]
        cfg = builder.build_pipeline_bar(stages, "恒瑞医药")
        assert len(cfg.series) == 2
        names = {s["name"] for s in cfg.series}
        assert names == {"总数", "创新药"}

    def test_pipeline_bar_empty_no_crash(self, builder):
        cfg = builder.build_pipeline_bar([], "恒瑞医药")
        assert cfg.chart_type == "bar"

    def test_score_bar_colors_by_score(self, builder):
        dims = [{"name": "财务质量", "score": 35.0, "weight": 0.15},   # 红
                {"name": "研发实力", "score": 60.0, "weight": 0.15},   # 黄
                {"name": "管线价值", "score": 80.0, "weight": 0.15}]   # 绿
        cfg = builder.build_score_bar(dims, "恒瑞医药")
        colors = [item["itemStyle"]["color"] for item in cfg.series[0]["data"]]
        assert "#ee6666" in colors   # 红色存在
        assert "#91cc75" in colors   # 绿色存在

    def test_build_from_score_result_generates_charts(self, builder, dims):
        trends = [{"metric": "营业总收入",
                   "points": [{"year": 2023, "value": 228.0, "unit": "亿元"}]}]
        stages = [{"stage": "III期", "count": 3, "innovative": 2}]
        charts = builder.build_from_score_result(dims, trends, stages, "恒瑞医药")
        assert len(charts) >= 3   # 雷达图 + 趋势图 + 管线图
        types = {c.chart_type for c in charts}
        assert "radar" in types
        assert "line" in types
        assert "bar" in types

    def test_build_from_score_result_empty_no_crash(self, builder):
        charts = builder.build_from_score_result([], [], [], "恒瑞医药")
        assert isinstance(charts, list)


# ── M3 证据收集 ───────────────────────────────────────────────────────────────

class TestM3EvidenceCollector:
    """M3：PharmaEvidenceCollector 相关度、去重、标签、缺失检测。"""

    @pytest.fixture
    def collector(self):
        from agent.tools.evidence_tools import PharmaEvidenceCollector
        return PharmaEvidenceCollector()

    @pytest.fixture
    def raw_items(self):
        return [
            {"kind": "announcement", "title": "创新药III期临床入组完成",
             "date": "2024-03-01", "source": "SSE",
             "summary": "公司创新药A完成III期临床入组，预计年底揭盲"},
            {"kind": "news", "title": "医保谈判结果公布",
             "date": "2024-02-15", "source": "财联社",
             "summary": "创新药纳入医保目录，价格降幅约30%"},
            {"kind": "financial_note", "title": "研发费用附注",
             "date": "2024-04-01", "source": "年报",
             "summary": "研发费用同比增长25%，管线持续扩充"},
            {"kind": "announcement", "title": "创新药III期临床入组完成",
             "date": "2024-03-01", "source": "SSE",
             "summary": "重复条目"},
        ]

    def test_deduplication(self, collector, raw_items):
        bundle = collector.collect("创新药", "600276", "恒瑞医药", raw_items=raw_items)
        assert len(bundle.items) == 3

    def test_no_missing_when_all_kinds_present(self, collector, raw_items):
        bundle = collector.collect("创新药", "600276", "恒瑞医药", raw_items=raw_items)
        assert bundle.missing_types == []

    def test_missing_detected_when_empty(self, collector):
        bundle = collector.collect("研发", "600276", "恒瑞医药", raw_items=[])
        assert "announcement" in bundle.missing_types
        assert "financial_note" in bundle.missing_types
        assert "news" in bundle.missing_types

    def test_missing_detected_partial(self, collector):
        items = [{"kind": "announcement", "title": "公告", "date": "",
                  "source": "", "summary": "内容"}]
        bundle = collector.collect("研发", "600276", "恒瑞医药", raw_items=items)
        assert "announcement" not in bundle.missing_types
        assert "news" in bundle.missing_types

    def test_relevance_positive(self, collector, raw_items):
        bundle = collector.collect("创新药临床", "600276", "恒瑞医药", raw_items=raw_items)
        for item in bundle.items:
            assert item.relevance > 0

    def test_sorted_by_relevance_desc(self, collector, raw_items):
        bundle = collector.collect("创新药临床", "600276", "恒瑞医药", raw_items=raw_items)
        scores = [item.relevance for item in bundle.items]
        assert scores == sorted(scores, reverse=True)

    def test_announcement_higher_base_relevance_than_news(self, collector):
        items = [
            {"kind": "announcement", "title": "公告", "date": "", "source": "", "summary": "内容"},
            {"kind": "news", "title": "新闻", "date": "", "source": "", "summary": "内容"},
        ]
        bundle = collector.collect("", "600276", "恒瑞医药", raw_items=items)
        ann = next(i for i in bundle.items if i.kind == "announcement")
        news = next(i for i in bundle.items if i.kind == "news")
        assert ann.relevance > news.relevance

    def test_tags_extracted(self, collector, raw_items):
        bundle = collector.collect("创新药", "600276", "恒瑞医药", raw_items=raw_items)
        all_tags = [tag for item in bundle.items for tag in item.tags]
        assert "临床试验" in all_tags
        assert "医保" in all_tags

    def test_items_capped_at_max(self, collector):
        many = [
            {"kind": "news", "title": f"新闻{i}", "date": "", "source": "", "summary": f"内容{i}"}
            for i in range(20)
        ]
        bundle = collector.collect("", "600276", "恒瑞医药", raw_items=many)
        assert len(bundle.items) <= 10

    def test_empty_title_and_summary_skipped(self, collector):
        items = [
            {"kind": "news", "title": "", "date": "", "source": "", "summary": ""},
            {"kind": "announcement", "title": "有效公告", "date": "", "source": "", "summary": "内容"},
        ]
        bundle = collector.collect("", "600276", "恒瑞医药", raw_items=items)
        assert len(bundle.items) == 1


# ── M3 预警规则 ───────────────────────────────────────────────────────────────

class TestM3WarningRules:
    """M3：PharmaDecisionTool 预警规则覆盖各类风险场景。"""

    @pytest.fixture
    def tool(self):
        from agent.tools.pharma_decision_tools import PharmaDecisionTool
        return PharmaDecisionTool()

    def test_no_warnings_for_clean_data(self, tool):
        fd = {"gross_margin": 72.0, "net_margin": 20.0, "roe": 18.0,
              "debt_ratio": 25.0, "rd_ratio": 16.0, "revenue": 2.5e10,
              "revenue_growth": 15.0, "ar_ratio": 0.12, "cashflow_quality": 1.1,
              "operating_cashflow": 3e9}
        pd_ = {"pipeline_total": 15, "pipeline_phase3": 4, "recent_approvals": 2,
               "trial_failures": 0, "phase3_failures": 0,
               "regulatory_total": 0, "regulatory_high_risk": 0,
               "sentiment_score": 0.4, "negative_news_ratio": 0.15}
        result = tool.analyze("600276", "恒瑞医药", 2024, financial_data=fd, pipeline_data=pd_)
        risk_warnings = [w for w in result.warnings if "风险" in w or "关注" in w]
        assert len(risk_warnings) == 0

    def test_high_debt_ratio_triggers_warning(self, tool):
        result = tool.analyze("X", "X", 2024, financial_data={"debt_ratio": 72.0})
        assert any("资产负债率" in w for w in result.warnings)

    def test_high_ar_ratio_triggers_warning(self, tool):
        result = tool.analyze("X", "X", 2024, financial_data={"ar_ratio": 0.45})
        assert any("应收账款" in w for w in result.warnings)

    def test_negative_cashflow_with_positive_profit_triggers_warning(self, tool):
        result = tool.analyze("X", "X", 2024,
                              financial_data={"operating_cashflow": -1e8, "net_profit": 1e8})
        assert any("现金流" in w for w in result.warnings)

    def test_revenue_decline_triggers_warning(self, tool):
        result = tool.analyze("X", "X", 2024, financial_data={"revenue_growth": -15.0})
        assert any("营收" in w for w in result.warnings)

    def test_phase3_failure_triggers_warning(self, tool):
        result = tool.analyze("X", "X", 2024, pipeline_data={"phase3_failures": 2})
        assert any("III 期" in w for w in result.warnings)

    def test_severe_price_cut_triggers_warning(self, tool):
        result = tool.analyze("X", "X", 2024, pipeline_data={"avg_price_cut_ratio": 0.65})
        assert any("集采" in w for w in result.warnings)

    def test_small_pipeline_triggers_warning(self, tool):
        result = tool.analyze("X", "X", 2024, pipeline_data={"pipeline_total": 2})
        assert any("管线" in w for w in result.warnings)

    def test_high_regulatory_risk_triggers_warning(self, tool):
        result = tool.analyze("X", "X", 2024, pipeline_data={"regulatory_high_risk": 2})
        assert any("合规" in w for w in result.warnings)

    def test_high_negative_news_triggers_warning(self, tool):
        result = tool.analyze("X", "X", 2024,
                              pipeline_data={"negative_news_ratio": 0.6})
        assert any("舆情" in w for w in result.warnings)

    def test_high_impact_negative_triggers_warning(self, tool):
        result = tool.analyze("X", "X", 2024,
                              pipeline_data={"high_impact_negative": 3})
        assert any("舆情" in w for w in result.warnings)

    def test_data_missing_warning_included(self, tool):
        result = tool.analyze("X", "X", 2024)
        assert any("数据缺失" in w for w in result.warnings)

    def test_warnings_are_strings(self, tool):
        result = tool.analyze("X", "X", 2024,
                              financial_data={"debt_ratio": 75.0},
                              pipeline_data={"phase3_failures": 2})
        for w in result.warnings:
            assert isinstance(w, str) and len(w) > 0


# ── M3 MedicalAnalyzer 端到端（图表+证据+预警）────────────────────────────────

class TestM3MedicalAnalyzerFull:
    """M3：MedicalAnalyzer 端到端验证图表、证据、预警字段完整性。"""

    def test_charts_generated_from_db(self, session_factory):
        """conftest 有财务数据，应生成至少1张图表。"""
        from agent.integration.medical_analyzer import MedicalAnalyzer
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(db, "600276", "恒瑞医药", 2024)
        assert isinstance(result.charts, list)
        assert len(result.charts) >= 1

    def test_charts_have_required_fields(self, session_factory):
        from agent.integration.medical_analyzer import MedicalAnalyzer
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(db, "600276", "恒瑞医药", 2024)
        for c in result.charts:
            assert "chart_type" in c
            assert "title" in c
            assert "series" in c
            assert "extra" in c

    def test_radar_chart_present(self, session_factory):
        from agent.integration.medical_analyzer import MedicalAnalyzer
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(db, "600276", "恒瑞医药", 2024)
        types = {c["chart_type"] for c in result.charts}
        assert "radar" in types

    def test_evidence_has_relevance_and_tags(self, session_factory):
        from agent.integration.medical_analyzer import MedicalAnalyzer
        raw = [
            {"kind": "announcement", "title": "创新药获批", "date": "2024-01-01",
             "source": "SSE", "summary": "创新药A获得NDA批准上市"},
            {"kind": "news", "title": "集采结果", "date": "2024-02-01",
             "source": "财联社", "summary": "仿制药集采中标，价格降幅20%"},
        ]
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(
                db, "600276", "恒瑞医药", 2024,
                query="创新药审批进展", raw_evidence=raw
            )
        assert len(result.evidence) == 2
        for e in result.evidence:
            assert "relevance" in e
            assert "tags" in e
            assert e["relevance"] > 0

    def test_evidence_sorted_by_relevance(self, session_factory):
        from agent.integration.medical_analyzer import MedicalAnalyzer
        raw = [
            {"kind": "news", "title": "无关新闻", "date": "", "source": "", "summary": "天气预报"},
            {"kind": "announcement", "title": "创新药临床进展", "date": "", "source": "",
             "summary": "创新药III期临床取得积极进展"},
        ]
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(
                db, "600276", "恒瑞医药", 2024,
                query="创新药临床", raw_evidence=raw
            )
        if len(result.evidence) >= 2:
            scores = [e["relevance"] for e in result.evidence]
            assert scores == sorted(scores, reverse=True)

    def test_warnings_deduplicated(self, session_factory):
        from agent.integration.medical_analyzer import MedicalAnalyzer
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(db, "600276", "恒瑞医药", 2024)
        assert len(result.warnings) == len(set(result.warnings))

    def test_financial_trend_chart_from_db(self, session_factory):
        """conftest 有 IncomeStatementHot，应生成趋势折线图。"""
        from agent.integration.medical_analyzer import MedicalAnalyzer
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(db, "600276", "恒瑞医药", 2024)
        line_charts = [c for c in result.charts if c["chart_type"] == "line"]
        assert len(line_charts) >= 1

    def test_pipeline_chart_from_db(self, session_factory):
        """conftest 有 DrugApprovalHot，应生成管线分布图。"""
        from agent.integration.medical_analyzer import MedicalAnalyzer
        with session_factory() as db:
            result = MedicalAnalyzer().analyze(db, "600276", "恒瑞医药", 2024)
        bar_charts = [c for c in result.charts if c["chart_type"] == "bar"]
        assert len(bar_charts) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
