"""AnalysisService 单元测试：评分算法、快照构建、信号判断。"""

from __future__ import annotations

import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 模块级 patch：在导入前生效
_mock_bootstrap = MagicMock()
_mock_bootstrap.check_database_health = MagicMock(return_value={"available": True, "status": "ok"})
_mock_bootstrap.init_application_database = MagicMock()

_test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

with patch.dict("sys.modules", {"app.bootstrap": _mock_bootstrap}):
    with patch("app.core.database.session._build_engine", return_value=_test_engine):
        from app.core.database.base import Base
        import app.core.database.models as _models  # noqa: F401
        from app.core.database.models.company import CompanyMaster
        from app.core.database.models.financial_hot import (
            BalanceSheetHot,
            CashflowStatementHot,
            FinancialMetricHot,
            IncomeStatementHot,
        )
        from app.core.database.models.announcement_hot import (
            AnnouncementStructuredHot,
            DrugApprovalHot,
            RegulatoryRiskEventHot,
        )
        from app.core.database.models.news_hot import NewsCompanyMapHot, NewsRawHot
        from app.router.analysis_service import (
            AnalysisService,
            _score_metric,
            _score_to_level,
            METRIC_RULES,
        )

Base.metadata.create_all(_test_engine)
_SessionLocal = sessionmaker(bind=_test_engine, class_=Session, autocommit=False, autoflush=False)


# ===========================================================================
# 测试数据 fixture
# ===========================================================================

@pytest.fixture(scope="module")
def db():
    """返回预填充测试数据的 SQLite 会话。"""
    session = _SessionLocal()
    today = date.today()

    session.add_all([
        CompanyMaster(
            stock_code="600276",
            stock_name="恒瑞医药",
            full_name="江苏恒瑞医药股份有限公司",
            exchange="SSE",
            industry_level1="医药生物",
            industry_level2="创新药",
            listing_date=today,
            status="active",
            alias_json=["恒瑞"],
            source_type="manual",
            source_url="https://example.com",
        ),
        CompanyMaster(
            stock_code="603259",
            stock_name="药明康德",
            full_name="药明康德新药开发有限公司",
            exchange="SSE",
            industry_level1="医药生物",
            industry_level2="医药外包",
            listing_date=today,
            status="active",
            source_type="manual",
            source_url="https://example.com",
        ),
        # 2024 年数据
        IncomeStatementHot(
            stock_code="600276",
            report_date=date(2024, 12, 31),
            fiscal_year=2024,
            report_type="annual",
            revenue=Decimal("10000.00"),
            gross_profit=Decimal("7000.00"),
            net_profit=Decimal("2000.00"),
            rd_expense=Decimal("1500.00"),
            eps=Decimal("1.20"),
            source_type="manual",
            source_url="https://example.com",
        ),
        BalanceSheetHot(
            stock_code="600276",
            report_date=date(2024, 12, 31),
            fiscal_year=2024,
            report_type="annual",
            total_assets=Decimal("50000.00"),
            total_liabilities=Decimal("15000.00"),
            equity=Decimal("35000.00"),
            source_type="manual",
            source_url="https://example.com",
        ),
        CashflowStatementHot(
            stock_code="600276",
            report_date=date(2024, 12, 31),
            fiscal_year=2024,
            report_type="annual",
            operating_cashflow=Decimal("3000.00"),
            source_type="manual",
            source_url="https://example.com",
        ),
        FinancialMetricHot(
            stock_code="600276",
            report_date=date(2024, 12, 31),
            fiscal_year=2024,
            metric_name="gross_margin",
            metric_value=Decimal("0.70"),
            metric_unit="ratio",
            calc_method="manual",
        ),
        FinancialMetricHot(
            stock_code="600276",
            report_date=date(2024, 12, 31),
            fiscal_year=2024,
            metric_name="rd_ratio",
            metric_value=Decimal("0.15"),
            metric_unit="ratio",
            calc_method="manual",
        ),
        # 2023 年数据（用于增长率计算）
        IncomeStatementHot(
            stock_code="600276",
            report_date=date(2023, 12, 31),
            fiscal_year=2023,
            report_type="annual",
            revenue=Decimal("8000.00"),
            gross_profit=Decimal("5600.00"),
            net_profit=Decimal("1600.00"),
            rd_expense=Decimal("1200.00"),
            eps=Decimal("1.00"),
            source_type="manual",
            source_url="https://example.com",
        ),
        BalanceSheetHot(
            stock_code="600276",
            report_date=date(2023, 12, 31),
            fiscal_year=2023,
            report_type="annual",
            total_assets=Decimal("45000.00"),
            total_liabilities=Decimal("13500.00"),
            equity=Decimal("31500.00"),
            source_type="manual",
            source_url="https://example.com",
        ),
        # 公告数据
        AnnouncementStructuredHot(
            stock_code="600276",
            announcement_id="ANN001",
            category="业绩预告",
            signal_type="opportunity",
            risk_level="low",
            summary_text="预计2024年净利润同比增长20%",
        ),
        DrugApprovalHot(
            stock_code="600276",
            drug_name="创新药A",
            approval_type="上市批准",
            approval_date=date(2024, 6, 1),
            source_type="manual",
        ),
        RegulatoryRiskEventHot(
            stock_code="600276",
            risk_type="环保处罚",
            risk_level="low",
            event_date=date(2024, 3, 15),
            summary_text="因环保问题被罚款10万元",
            source_type="manual",
        ),
        # 新闻数据
        NewsRawHot(
            id=1,
            news_uid="NEWS001",
            title="恒瑞医药新药获批",
            content="恒瑞医药创新药获得NMPA批准上市",
            publish_time=datetime(2024, 6, 1, 10, 0, 0),
            source_name="财经网",
            source_url="https://example.com/news1",
        ),
        NewsCompanyMapHot(
            news_id=1,
            stock_code="600276",
            impact_direction="positive",
            reason_text="新药获批将带来新增长点",
        ),
    ])
    session.commit()
    yield session
    session.close()


# ===========================================================================
# 评分算法测试
# ===========================================================================

class TestScoringAlgorithm:
    """测试 _score_metric 和 _score_to_level 函数。"""

    def test_score_metric_higher_better_excellent(self):
        """higher_better=True，值超过 good 阈值应得 90+ 分。"""
        rule = METRIC_RULES["毛利率"]
        score = _score_metric(70.0, rule)
        assert score >= 90

    def test_score_metric_higher_better_good(self):
        """higher_better=True，值在 avg 和 good 之间应得 60-90 分。"""
        rule = METRIC_RULES["毛利率"]
        score = _score_metric(50.0, rule)
        assert 60 <= score < 90

    def test_score_metric_higher_better_poor(self):
        """higher_better=True，值在 poor 和 avg 之间应得 30-60 分。"""
        rule = METRIC_RULES["毛利率"]
        score = _score_metric(30.0, rule)
        assert 30 <= score < 60

    def test_score_metric_higher_better_very_poor(self):
        """higher_better=True，值低于 poor 应得 0-30 分。"""
        rule = METRIC_RULES["毛利率"]
        score = _score_metric(10.0, rule)
        assert 0 <= score < 30

    def test_score_metric_lower_better_excellent(self):
        """higher_better=False，值低于 good 阈值应得 90+ 分。"""
        rule = METRIC_RULES["资产负债率"]
        score = _score_metric(20.0, rule)
        assert score >= 90

    def test_score_metric_lower_better_good(self):
        """higher_better=False，值在 good 和 avg 之间应得 60-90 分。"""
        rule = METRIC_RULES["资产负债率"]
        score = _score_metric(35.0, rule)
        assert 60 <= score < 90

    def test_score_metric_lower_better_poor(self):
        """higher_better=False，值在 avg 和 poor 之间应得 30-60 分。"""
        rule = METRIC_RULES["资产负债率"]
        score = _score_metric(55.0, rule)
        assert 30 <= score < 60

    def test_score_metric_lower_better_very_poor(self):
        """higher_better=False，值高于 poor 应得 0-30 分。"""
        rule = METRIC_RULES["资产负债率"]
        score = _score_metric(75.0, rule)
        assert 0 <= score < 30

    def test_score_to_level_excellent(self):
        """总分 >= 80 应为「优秀」。"""
        assert _score_to_level(85.0) == "优秀"

    def test_score_to_level_good(self):
        """总分 65-79 应为「良好」。"""
        assert _score_to_level(70.0) == "良好"

    def test_score_to_level_average(self):
        """总分 45-64 应为「一般」。"""
        assert _score_to_level(50.0) == "一般"

    def test_score_to_level_poor(self):
        """总分 < 45 应为「较差」。"""
        assert _score_to_level(40.0) == "较差"


# ===========================================================================
# AnalysisService 核心方法测试
# ===========================================================================

class TestAnalysisService:
    """测试 AnalysisService 的核心业务逻辑。"""

    def test_diagnose_returns_result_for_known_company(self, db):
        """diagnose 已知公司应返回 DiagnoseResult。"""
        service = AnalysisService()
        result = service.diagnose(db, "600276", 2024)
        assert result is not None
        assert result.stock_code == "600276"
        assert result.stock_name == "恒瑞医药"
        assert result.year == 2024
        assert result.total_score > 0
        assert result.level in ["优秀", "良好", "一般", "较差"]

    def test_diagnose_dimensions_structure(self, db):
        """diagnose 返回的 dimensions 应包含正确字段。"""
        service = AnalysisService()
        result = service.diagnose(db, "600276", 2024)
        assert len(result.dimensions) > 0
        for dim in result.dimensions:
            assert dim.name in ["盈利能力", "偿债能力", "成长性", "创新投入"]
            assert 0 <= dim.score <= 100
            assert isinstance(dim.metrics, dict)
            assert dim.comment != ""

    def test_diagnose_calculates_growth_rates(self, db):
        """diagnose 应正确计算增长率（需要多年数据）。"""
        service = AnalysisService()
        result = service.diagnose(db, "600276", 2024)
        # 2024 营收 10000，2023 营收 8000，增长率应为 25%
        growth_dim = next((d for d in result.dimensions if d.name == "成长性"), None)
        assert growth_dim is not None
        assert "营业总收入增长率" in growth_dim.metrics
        assert growth_dim.metrics["营业总收入增长率"]["value"] == 25.0

    def test_diagnose_unknown_company_raises_error(self, db):
        """diagnose 未知公司应抛出 ValueError。"""
        service = AnalysisService()
        with pytest.raises(ValueError, match="company not found"):
            service.diagnose(db, "999999", 2024)

    def test_diagnose_no_data_returns_none(self, db):
        """diagnose 公司存在但无财务数据应返回 None。"""
        service = AnalysisService()
        result = service.diagnose(db, "603259", 2024)
        assert result is None

    def test_compare_metric_returns_sorted_list(self, db):
        """compare_metric 应返回按指标值排序的列表。"""
        service = AnalysisService()
        result = service.compare_metric(db, "毛利率", 2024, ["600276"])
        assert result["metric"] == "毛利率"
        assert result["year"] == 2024
        assert len(result["data"]) == 1
        assert result["data"][0]["stock_code"] == "600276"
        assert result["data"][0]["value"] == 70.0
        assert result["data"][0]["unit"] == "%"

    def test_compare_metric_alias_resolution(self, db):
        """compare_metric 应正确解析指标别名。"""
        service = AnalysisService()
        result = service.compare_metric(db, "营收", 2024, ["600276"])
        assert result["metric"] == "营业总收入"

    def test_get_metric_trend_returns_time_series(self, db):
        """get_metric_trend 应返回多年趋势数据。"""
        service = AnalysisService()
        result = service.get_metric_trend(db, "600276", "毛利率")
        assert result["stock_code"] == "600276"
        assert result["metric"] == "毛利率"
        assert len(result["trend"]) == 2  # 2023 和 2024
        assert result["trend"][0]["year"] in [2023, 2024]
        assert "value" in result["trend"][0]

    def test_get_metric_trend_unknown_company_raises_error(self, db):
        """get_metric_trend 未知公司应抛出 ValueError。"""
        service = AnalysisService()
        with pytest.raises(ValueError, match="company not found"):
            service.get_metric_trend(db, "999999", "毛利率")

    def test_scan_risks_returns_risk_signals(self, db):
        """scan_risks 应返回风险和机会信号。"""
        service = AnalysisService()
        results = service.scan_risks(db, ["600276"])
        assert len(results) == 1
        item = results[0]
        assert item["stock_code"] == "600276"
        assert item["risk_level"] in ["green", "yellow", "red"]
        assert isinstance(item["risks"], list)
        assert isinstance(item["opportunities"], list)

    def test_scan_risks_financial_signals(self, db):
        """scan_risks 应识别财务指标信号。"""
        service = AnalysisService()
        results = service.scan_risks(db, ["600276"])
        item = results[0]
        # 毛利率 70% 应触发机会信号
        opportunities = [o for o in item["opportunities"] if "毛利率" in o["signal"]]
        assert len(opportunities) > 0

    def test_scan_risks_announcement_signals(self, db):
        """scan_risks 应包含公告信号。"""
        service = AnalysisService()
        results = service.scan_risks(db, ["600276"])
        item = results[0]
        # 应包含药品审批机会信号
        drug_signals = [o for o in item["opportunities"] if "药品审批" in o["signal"]]
        assert len(drug_signals) > 0
        # 应包含监管风险信号
        risk_signals = [r for r in item["risks"] if "环保" in r.get("signal", "") or "监管" in r.get("signal", "")]
        assert len(risk_signals) > 0

    def test_scan_risks_news_signals(self, db):
        """scan_risks 应包含新闻舆情信号。"""
        service = AnalysisService()
        results = service.scan_risks(db, ["600276"])
        item = results[0]
        # 应包含正面新闻信号
        news_signals = [o for o in item["opportunities"] if "新闻舆情" in o["signal"]]
        assert len(news_signals) > 0

    def test_scan_risks_fallback_to_db_companies(self, db):
        """scan_risks 无效代码时应回退到数据库中的公司。"""
        service = AnalysisService()
        results = service.scan_risks(db, ["999999"])
        # 应返回数据库中前 3 家公司（这里只有 2 家）
        assert len(results) <= 3


# ===========================================================================
# 边界情况测试
# ===========================================================================

class TestEdgeCases:
    """测试边界情况和异常处理。"""

    def test_diagnose_year_not_exact_match_uses_closest(self, db):
        """diagnose 年份不精确匹配时应使用最接近的年份。"""
        service = AnalysisService()
        result = service.diagnose(db, "600276", 2025)
        # 应回退到 2024 年数据
        assert result is not None
        assert result.year == 2024

    def test_diagnose_handles_missing_metrics_gracefully(self, db):
        """diagnose 缺少部分指标时应跳过该指标。"""
        # 删除研发费用率指标
        db.query(FinancialMetricHot).filter(
            FinancialMetricHot.stock_code == "600276",
            FinancialMetricHot.metric_name == "rd_ratio",
        ).delete()
        db.commit()

        service = AnalysisService()
        result = service.diagnose(db, "600276", 2024)
        # 应仍能返回结果，但创新投入维度可能缺失或分数较低
        assert result is not None

    def test_compare_metric_empty_codes_uses_fallback(self, db):
        """compare_metric 空代码列表应使用数据库回退。"""
        service = AnalysisService()
        result = service.compare_metric(db, "毛利率", 2024, [])
        # 应返回数据库中前 3 家公司
        assert len(result["data"]) <= 3

    def test_scan_risks_no_financial_data_returns_empty_signals(self, db):
        """scan_risks 无财务数据时应返回空信号列表。"""
        service = AnalysisService()
        results = service.scan_risks(db, ["603259"])
        # 603259 无财务数据，应返回空或极少信号
        if results:
            item = results[0]
            assert item["stock_code"] == "603259"
            assert item["risk_level"] == "green"
