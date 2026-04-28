"""路由层测试：chat / stock / analysis 端点，使用 SQLite 内存库隔离 MySQL。

隔离策略：
  - patch app.bootstrap 阻止 MySQL 健康检查
  - patch app.core.database.session._build_engine 返回 SQLite 引擎
  - 通过 dependency_overrides 注入 SQLite 会话
"""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# 模块级 patch：在任何项目模块导入前生效
# ---------------------------------------------------------------------------
_mock_bootstrap = MagicMock()
_mock_bootstrap.check_database_health = MagicMock(
    return_value={"available": True, "status": "ok"}
)
_mock_bootstrap.init_application_database = MagicMock()

_test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

with patch.dict("sys.modules", {"app.bootstrap": _mock_bootstrap}):
    with patch("app.core.database.session._build_engine", return_value=_test_engine):
        import main as app_module
        from app.core.database.base import Base
        import app.core.database.models as _models  # noqa: F401 — 注册所有 ORM 模型
        from app.core.database.models.company import CompanyMaster
        from app.core.database.models.financial_hot import (
            BalanceSheetHot,
            CashflowStatementHot,
            FinancialMetricHot,
            IncomeStatementHot,
            StockDailyHot,
        )
        from app.core.database.models.user import User
        from app.core.database import session as session_mod

app = app_module.app
Base.metadata.create_all(_test_engine)

_SessionLocal = sessionmaker(
    bind=_test_engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# 测试数据 fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db():
    """返回预填充了测试数据的 SQLite 会话。"""
    session = _SessionLocal()
    today = date.today()

    session.add_all([
        User(id=1, username="demo_user", password_hash="x", role="user", status="active"),
        CompanyMaster(
            stock_code="600276", stock_name="恒瑞医药",
            full_name="江苏恒瑞医药股份有限公司", exchange="SSE",
            industry_level1="医药生物", industry_level2="创新药",
            listing_date=today, status="active",
            alias_json=["恒瑞"], source_type="manual",
            source_url="https://example.com",
        ),
        StockDailyHot(
            stock_code="600276", trade_date=today,
            open_price=Decimal("45.00"), close_price=Decimal("46.00"),
            high_price=Decimal("47.00"), low_price=Decimal("44.00"),
            volume=100000, turnover=Decimal("4600000.00"),
            source_type="manual",
        ),
        IncomeStatementHot(
            stock_code="600276", report_date=today,
            fiscal_year=today.year, report_type="annual",
            revenue=Decimal("10000.00"), gross_profit=Decimal("7000.00"),
            net_profit=Decimal("2000.00"), net_profit_deducted=Decimal("1900.00"),
            rd_expense=Decimal("1500.00"), eps=Decimal("1.20"),
            source_type="manual", source_url="https://example.com",
        ),
        BalanceSheetHot(
            stock_code="600276", report_date=today,
            fiscal_year=today.year, report_type="annual",
            total_assets=Decimal("50000.00"), total_liabilities=Decimal("15000.00"),
            cash=Decimal("8000.00"), equity=Decimal("35000.00"),
            goodwill=Decimal("100.00"),
            source_type="manual", source_url="https://example.com",
        ),
        CashflowStatementHot(
            stock_code="600276", report_date=today,
            fiscal_year=today.year, report_type="annual",
            operating_cashflow=Decimal("3000.00"),
            investing_cashflow=Decimal("-500.00"),
            financing_cashflow=Decimal("200.00"),
            free_cashflow=Decimal("2500.00"),
            source_type="manual", source_url="https://example.com",
        ),
        FinancialMetricHot(
            stock_code="600276", report_date=today,
            fiscal_year=today.year, metric_name="gross_margin",
            metric_value=Decimal("0.70"), metric_unit="ratio",
            calc_method="manual", source_ref_json={"src": "income"},
        ),
        FinancialMetricHot(
            stock_code="600276", report_date=today,
            fiscal_year=today.year, metric_name="rd_ratio",
            metric_value=Decimal("0.15"), metric_unit="ratio",
            calc_method="manual", source_ref_json={"src": "income"},
        ),
    ])
    session.commit()
    yield session
    session.close()


@pytest.fixture(scope="module")
def client(db):
    """TestClient，将 get_db 依赖替换为 SQLite 会话。"""
    def override_get_db():
        yield db

    app.dependency_overrides[session_mod.get_db] = override_get_db
    # raise_server_exceptions=False：让 500 以 HTTP 响应返回而非抛出异常
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ===========================================================================
# chat 路由
# ===========================================================================

class TestChatRouter:
    def test_post_chat_returns_200(self, client):
        """/api/chat 应返回 200 和 answer 字段。"""
        resp = client.post("/api/chat", json={
            "message": "你好",
            "history": [],
            "targets": [],
        })
        assert resp.status_code == 200
        assert "answer" in resp.json()

    def test_post_chat_missing_message_returns_422(self, client):
        """/api/chat 缺少 message 字段应返回 422。"""
        resp = client.post("/api/chat", json={"history": []})
        assert resp.status_code == 422

    def test_post_chat_empty_message_returns_422(self, client):
        """/api/chat message 为空字符串应返回 422（min_length=1）。"""
        resp = client.post("/api/chat", json={"message": "", "history": []})
        assert resp.status_code == 422

    def test_post_chat_stream_returns_event_stream(self, client):
        """/api/chat/stream 应返回 text/event-stream 内容类型。"""
        resp = client.post("/api/chat/stream", json={
            "message": "分析恒瑞医药",
            "history": [],
            "targets": [],
        })
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

    def test_post_chat_stream_body_contains_sse_data(self, client):
        """/api/chat/stream 响应体应包含 SSE data: 行。"""
        resp = client.post("/api/chat/stream", json={
            "message": "测试",
            "history": [],
            "targets": [],
        })
        assert b"data:" in resp.content

    def test_post_chat_stream_ends_with_done(self, client):
        """/api/chat/stream 最后一条 SSE 应包含 done: true。"""
        resp = client.post("/api/chat/stream", json={
            "message": "测试",
            "history": [],
            "targets": [],
        })
        assert b'"done": true' in resp.content or b'"done":true' in resp.content

    def test_upload_pdf_returns_501(self, client):
        """/api/upload_pdf 暂未实现，应返回 501。"""
        resp = client.post(
            "/api/upload_pdf",
            files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert resp.status_code == 501

    def test_get_chat_history_returns_200(self, client):
        """/api/chat/history 应返回 200 和 total / records 字段。"""
        resp = client.get("/api/chat/history?user_id=1&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "records" in data

    def test_post_chat_with_targets(self, client):
        """/api/chat 携带 targets 时应正常处理。"""
        resp = client.post("/api/chat", json={
            "message": "分析这只股票",
            "history": [],
            "targets": [{"symbol": "600276", "name": "恒瑞医药", "type": "stock"}],
        })
        assert resp.status_code == 200

    def test_post_chat_with_history(self, client):
        """/api/chat 携带 history 时应正常处理。"""
        resp = client.post("/api/chat", json={
            "message": "继续分析",
            "history": [
                {"role": "user", "content": "分析恒瑞医药"},
                {"role": "assistant", "content": "恒瑞医药是创新药龙头。"},
            ],
            "targets": [],
        })
        assert resp.status_code == 200

    def test_post_chat_response_has_session_id(self, client):
        """/api/chat 响应应包含 session_id 字段。"""
        resp = client.post("/api/chat", json={
            "message": "测试会话",
            "history": [],
            "targets": [],
        })
        assert resp.status_code == 200
        assert "session_id" in resp.json()


# ===========================================================================
# stock 路由
# ===========================================================================

class TestStockRouter:
    def test_get_quote_known_symbol(self, client):
        """/api/stock/quote 已知股票代码应返回 200 和行情字段。"""
        resp = client.get("/api/stock/quote?symbol=600276")
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "600276"
        assert "price" in data
        assert "change_percent" in data
        assert "open" in data
        assert "high" in data
        assert "low" in data

    def test_get_quote_unknown_symbol_returns_404(self, client):
        """/api/stock/quote 未知代码应返回 404。"""
        resp = client.get("/api/stock/quote?symbol=999999")
        assert resp.status_code == 404

    def test_get_quote_missing_symbol_returns_422(self, client):
        """/api/stock/quote 缺少 symbol 参数应返回 422。"""
        resp = client.get("/api/stock/quote")
        assert resp.status_code == 422

    def test_get_quote_name_lookup(self, client):
        """/api/stock/quote 支持公司名称查询。"""
        resp = client.get("/api/stock/quote?symbol=恒瑞医药")
        assert resp.status_code == 200
        assert resp.json()["symbol"] == "600276"

    def test_get_kline_known_symbol(self, client):
        """/api/stock/kline 已知代码应返回列表。"""
        resp = client.get("/api/stock/kline?symbol=600276&days=30")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_kline_response_fields(self, client):
        """kline 每条记录应包含 date / open / high / low / close / volume。"""
        resp = client.get("/api/stock/kline?symbol=600276&days=30")
        items = resp.json()
        if items:
            item = items[0]
            for field in ("date", "open", "high", "low", "close", "volume"):
                assert field in item, f"kline 缺少字段 {field!r}"

    def test_get_kline_days_too_large_returns_422(self, client):
        """/api/stock/kline days 超出范围（>120）应返回 422。"""
        resp = client.get("/api/stock/kline?symbol=600276&days=200")
        assert resp.status_code == 422

    def test_get_kline_days_too_small_returns_422(self, client):
        """/api/stock/kline days 小于 5 应返回 422。"""
        resp = client.get("/api/stock/kline?symbol=600276&days=2")
        assert resp.status_code == 422

    def test_get_watchlist_returns_list(self, client):
        """/api/stock/watchlist 应返回列表。"""
        resp = client.get("/api/stock/watchlist?user_id=1")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_post_watchlist_add_known_symbol(self, client):
        """/api/stock/watchlist POST 已知代码应返回 200 和 symbol 字段。"""
        resp = client.post("/api/stock/watchlist", json={
            "user_id": 1,
            "symbol": "600276",
            "name": "恒瑞医药",
        })
        assert resp.status_code == 200
        assert resp.json()["symbol"] == "600276"

    def test_post_watchlist_unknown_symbol_returns_404(self, client):
        """/api/stock/watchlist POST 未知代码应返回 404。"""
        resp = client.post("/api/stock/watchlist", json={
            "user_id": 1,
            "symbol": "000000",
        })
        assert resp.status_code == 404

    def test_delete_watchlist_returns_200(self, client):
        """/api/stock/watchlist DELETE 应返回 200。"""
        resp = client.delete("/api/stock/watchlist?user_id=1&symbol=600276")
        assert resp.status_code == 200

    def test_get_companies_returns_200(self, client):
        """/api/stock/companies 应返回 200。"""
        resp = client.get("/api/stock/companies")
        assert resp.status_code == 200

    def test_get_company_dataset_known_symbol(self, client):
        """/api/stock/company 已知代码应返回 200。"""
        resp = client.get("/api/stock/company?symbol=600276")
        assert resp.status_code == 200

    def test_get_company_dataset_unknown_symbol_returns_404(self, client):
        """/api/stock/company 未知代码应返回 404。"""
        resp = client.get("/api/stock/company?symbol=999999")
        assert resp.status_code == 404

    def test_get_db_stats_returns_200(self, client):
        """/api/stock/db/stats 应返回 200。"""
        resp = client.get("/api/stock/db/stats")
        assert resp.status_code == 200


# ===========================================================================
# analysis 路由
# ===========================================================================

class TestAnalysisRouter:
    # --- /api/analysis/diagnose ---

    def test_get_diagnose_known_symbol_returns_200(self, client):
        """/api/analysis/diagnose 已知代码数据充足时应返回 200。"""
        resp = client.get(f"/api/analysis/diagnose?symbol=600276&year={date.today().year}")
        assert resp.status_code == 200

    def test_get_diagnose_unknown_symbol_returns_404(self, client):
        """/api/analysis/diagnose 未知代码应返回 404。"""
        resp = client.get("/api/analysis/diagnose?symbol=999999&year=2024")
        assert resp.status_code == 404

    def test_get_diagnose_missing_symbol_returns_422(self, client):
        """/api/analysis/diagnose 缺少 symbol 应返回 422。"""
        resp = client.get("/api/analysis/diagnose?year=2024")
        assert resp.status_code == 422

    def test_get_diagnose_response_schema(self, client):
        """diagnose 响应应包含所有必填字段。"""
        resp = client.get(f"/api/analysis/diagnose?symbol=600276&year={date.today().year}")
        assert resp.status_code == 200
        data = resp.json()
        for field in ("stock_code", "stock_name", "year", "total_score", "level",
                      "dimensions", "strengths", "weaknesses", "suggestion"):
            assert field in data, f"diagnose 响应缺少字段 {field!r}"
        assert isinstance(data["dimensions"], list)
        assert len(data["dimensions"]) > 0

    def test_get_diagnose_dimension_schema(self, client):
        """diagnose 每个 dimension 应包含 name / score / comment / metrics。"""
        resp = client.get(f"/api/analysis/diagnose?symbol=600276&year={date.today().year}")
        dim = resp.json()["dimensions"][0]
        for field in ("name", "score", "comment", "metrics"):
            assert field in dim, f"dimension 缺少字段 {field!r}"
        assert isinstance(dim["metrics"], dict)

    # --- /api/analysis/risks ---

    def test_get_risks_returns_200(self, client):
        """/api/analysis/risks 应返回 200。"""
        resp = client.get("/api/analysis/risks?symbols=600276")
        assert resp.status_code == 200

    def test_get_risks_response_schema(self, client):
        """risks 响应应包含 total / data 字段。"""
        resp = client.get("/api/analysis/risks?symbols=600276")
        data = resp.json()
        assert "total" in data
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_get_risks_item_schema(self, client):
        """risks 每条记录应包含 stock_code / risk_level / risks / opportunities。"""
        resp = client.get("/api/analysis/risks?symbols=600276")
        items = resp.json()["data"]
        if items:
            item = items[0]
            for field in ("stock_code", "risk_level", "risks", "opportunities"):
                assert field in item, f"risks item 缺少字段 {field!r}"

    def test_get_risks_unknown_symbol_falls_back_to_db(self, client):
        """risks 未知代码时服务层回退到数据库中的公司，仍返回 200。"""
        resp = client.get("/api/analysis/risks?symbols=999999")
        assert resp.status_code == 200
        assert "data" in resp.json()

    # --- /api/analysis/compare ---

    def test_get_compare_returns_200(self, client):
        """/api/analysis/compare 应返回 200。"""
        resp = client.get(
            f"/api/analysis/compare?metric=毛利率&year={date.today().year}&symbols=600276"
        )
        assert resp.status_code == 200

    def test_get_compare_response_schema(self, client):
        """compare 响应应包含 metric / year / data 字段。"""
        resp = client.get(
            f"/api/analysis/compare?metric=毛利率&year={date.today().year}&symbols=600276"
        )
        data = resp.json()
        assert "metric" in data
        assert "year" in data
        assert "data" in data

    def test_get_compare_metric_alias(self, client):
        """compare 支持中文别名，「营收」应映射到「营业总收入」。"""
        resp = client.get(
            f"/api/analysis/compare?metric=营收&year={date.today().year}&symbols=600276"
        )
        assert resp.status_code == 200
        assert resp.json()["metric"] == "营业总收入"

    def test_get_compare_missing_metric_returns_422(self, client):
        """/api/analysis/compare 缺少 metric 应返回 422。"""
        resp = client.get(f"/api/analysis/compare?year={date.today().year}&symbols=600276")
        assert resp.status_code == 422

    # --- /api/analysis/trend ---

    def test_get_trend_known_symbol(self, client):
        """/api/analysis/trend 已知代码应返回 200 和 trend 列表。"""
        resp = client.get("/api/analysis/trend?symbol=600276&metric=毛利率")
        assert resp.status_code == 200
        data = resp.json()
        assert "trend" in data
        assert isinstance(data["trend"], list)

    def test_get_trend_response_schema(self, client):
        """trend 响应应包含 stock_code / stock_name / metric / trend。"""
        resp = client.get("/api/analysis/trend?symbol=600276&metric=毛利率")
        data = resp.json()
        for field in ("stock_code", "stock_name", "metric", "trend"):
            assert field in data, f"trend 响应缺少字段 {field!r}"

    def test_get_trend_unknown_symbol_returns_404(self, client):
        """/api/analysis/trend 未知代码应返回 404。"""
        resp = client.get("/api/analysis/trend?symbol=999999&metric=毛利率")
        assert resp.status_code == 404

    def test_get_trend_missing_metric_returns_422(self, client):
        """/api/analysis/trend 缺少 metric 应返回 422。"""
        resp = client.get("/api/analysis/trend?symbol=600276")
        assert resp.status_code == 422

    def test_get_trend_missing_symbol_returns_422(self, client):
        """/api/analysis/trend 缺少 symbol 应返回 422。"""
        resp = client.get("/api/analysis/trend?metric=毛利率")
        assert resp.status_code == 422
