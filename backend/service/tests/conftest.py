from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app.core.database.models  # noqa: F401
from app.core.database.base import Base
from app.core.database.models.announcement_hot import (
    AnnouncementRawHot,
    AnnouncementStructuredHot,
    CentralizedProcurementEventHot,
    ClinicalTrialEventHot,
    DrugApprovalHot,
    RegulatoryRiskEventHot,
)
from app.core.database.models.company import CompanyIndustryMap, CompanyMaster, CompanyProfile, IndustryMaster
from app.core.database.models.financial_hot import (
    BalanceSheetHot,
    BusinessSegmentHot,
    CashflowStatementHot,
    FinancialMetricHot,
    FinancialNotesHot,
    IncomeStatementHot,
    StockDailyHot,
)
from app.core.database.models.macro_hot import MacroIndicatorHot
from app.core.database.models.news_hot import (
    IndustryImpactEventHot,
    NewsCompanyMapHot,
    NewsIndustryMapHot,
    NewsRawHot,
    NewsStructuredHot,
)
from app.core.database.models.user import User
from app.service.announcement_service import AnnouncementService
from app.service.announcement_write_service import AnnouncementWriteService
from app.service.cache_service import CacheService
from app.service.chat_service import ChatService
from app.service.company_service import CompanyService
from app.service.company_write_service import CompanyWriteService
from app.service.context import ServiceContext
from app.service.financial_service import FinancialService
from app.service.financial_write_service import FinancialWriteService
from app.service.ingest_gateway_service import IngestGatewayService
from app.service.macro_service import MacroService
from app.service.macro_write_service import MacroWriteService
from app.service.maintenance_service import MaintenanceService
from app.service.news_service import NewsService
from app.service.news_write_service import NewsWriteService
from app.service.retrieval_service import RetrievalService


class FakeVectorStore:
    def __init__(self) -> None:
        self.docs = [
            {
                "id": "ann-1",
                "doc_id": "announcement:1",
                "text": "恒瑞医药公告显示创新药临床试验取得积极进展。",
                "score": 0.93,
                "metadata": {
                    "doc_type": "announcement",
                    "stock_code": "600276",
                    "industry_code": "IND001",
                    "source_table": "announcement_raw_hot",
                    "source_pk": 1,
                },
            },
            {
                "id": "news-1",
                "doc_id": "news:1",
                "text": "创新药板块受政策支持，行业情绪改善。",
                "score": 0.88,
                "metadata": {
                    "doc_type": "news",
                    "stock_code": "600276",
                    "industry_code": "IND001",
                    "source_table": "news_raw_hot",
                    "source_pk": 1,
                },
            },
            {
                "id": "note-1",
                "doc_id": "financial_note:1",
                "text": "财报附注提到公司研发投入持续增长，多个创新药推进临床。",
                "score": 0.91,
                "metadata": {
                    "doc_type": "financial_note",
                    "stock_code": "600276",
                    "industry_code": "IND001",
                    "source_table": "financial_notes_hot",
                    "source_pk": 1,
                },
            },
        ]

    def search(self, query: str, *, top_k: int, filters: dict | None = None, doc_types: list[str] | None = None) -> list[dict]:
        filters = filters or {}
        allowed_doc_types = set(doc_types or [])
        results = []
        for doc in self.docs:
            meta = doc["metadata"]
            if allowed_doc_types and meta.get("doc_type") not in allowed_doc_types:
                continue
            matched = True
            for key, expected in filters.items():
                if expected is None:
                    continue
                if meta.get(key) != expected:
                    matched = False
                    break
            if matched:
                results.append(doc)
        return results[:top_k]

    def delete_by_source(self, *, doc_type: str, source_table: str, source_pks: list[int | str]) -> int:
        before = len(self.docs)
        pk_set = {str(x) for x in source_pks}
        self.docs = [
            d for d in self.docs
            if not (d["metadata"].get("doc_type") == doc_type and d["metadata"].get("source_table") == source_table and str(d["metadata"].get("source_pk")) in pk_set)
        ]
        return before - len(self.docs)


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="session")
def session_factory(engine):
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db:
        if db.query(CompanyMaster).count() == 0:
            old_day = date.today() - timedelta(days=400)
            old_dt = datetime.now(timezone.utc) - timedelta(days=400)
            user = User(username="tester", password_hash="hashed", role="user", status="active")
            company = CompanyMaster(
                stock_code="600276", stock_name="恒瑞医药", full_name="江苏恒瑞医药股份有限公司", exchange="SSE",
                industry_level1="医药生物", industry_level2="创新药", listing_date=date.today(), status="active",
                alias_json=["恒瑞", "Hengrui"], source_type="manual", source_url="https://example.com/company"
            )
            company_old = CompanyMaster(
                stock_code="600000", stock_name="老样本公司", full_name="老样本医药公司", exchange="SSE",
                industry_level1="医药生物", industry_level2="中药", listing_date=old_day, status="active",
                alias_json=["老样本"], source_type="manual", source_url="https://example.com/company-old"
            )
            profile = CompanyProfile(
                stock_code="600276", business_summary="公司聚焦创新药研发与商业化。", core_products_json=["创新药A"],
                main_segments_json=["抗肿瘤"], market_position="国内创新药龙头之一。", management_summary="管理层重视研发投入。"
            )
            industry1 = IndustryMaster(industry_code="IND001", industry_name="创新药", parent_industry_code=None, industry_level=1, description="创新药行业")
            industry2 = IndustryMaster(industry_code="IND002", industry_name="中药", parent_industry_code=None, industry_level=1, description="中药行业")
            industry_map = CompanyIndustryMap(stock_code="600276", industry_code="IND001", is_primary=1)

            income = IncomeStatementHot(stock_code="600276", report_date=date.today(), fiscal_year=date.today().year, report_type="annual", revenue=Decimal("1000.00"), gross_profit=Decimal("800.00"), net_profit=Decimal("300.00"), net_profit_deducted=Decimal("280.00"), rd_expense=Decimal("150.00"), eps=Decimal("0.50"), source_type="manual", source_url="https://example.com/income")
            income_old = IncomeStatementHot(stock_code="600000", report_date=old_day, fiscal_year=old_day.year, report_type="annual", revenue=Decimal("500.00"), net_profit=Decimal("50.00"), source_type="manual", source_url="https://example.com/old-income")
            balance = BalanceSheetHot(stock_code="600276", report_date=date.today(), fiscal_year=date.today().year, report_type="annual", total_assets=Decimal("5000.00"), total_liabilities=Decimal("1200.00"), cash=Decimal("900.00"), equity=Decimal("3800.00"), goodwill=Decimal("20.00"), source_type="manual", source_url="https://example.com/balance")
            cashflow = CashflowStatementHot(stock_code="600276", report_date=date.today(), fiscal_year=date.today().year, report_type="annual", operating_cashflow=Decimal("400.00"), investing_cashflow=Decimal("-100.00"), financing_cashflow=Decimal("50.00"), free_cashflow=Decimal("300.00"), source_type="manual", source_url="https://example.com/cashflow")
            metrics = [
                FinancialMetricHot(stock_code="600276", report_date=date.today(), fiscal_year=date.today().year, metric_name="gross_margin", metric_value=Decimal("0.80"), metric_unit="ratio", calc_method="manual", source_ref_json={"src": "income"}),
                FinancialMetricHot(stock_code="600276", report_date=date.today(), fiscal_year=date.today().year, metric_name="rd_ratio", metric_value=Decimal("0.15"), metric_unit="ratio", calc_method="manual", source_ref_json={"src": "income"}),
                FinancialMetricHot(stock_code="600000", report_date=old_day, fiscal_year=old_day.year, metric_name="gross_margin", metric_value=Decimal("0.20"), metric_unit="ratio", calc_method="manual", source_ref_json={"src": "old"}),
            ]
            note = FinancialNotesHot(stock_code="600276", report_date=date.today(), note_type="rd_pipeline", note_json={"pipeline": 3}, note_text="多个创新药推进临床。", source_type="manual", source_url="https://example.com/note")
            segment = BusinessSegmentHot(stock_code="600276", report_date=date.today(), segment_name="抗肿瘤药", segment_type="drug", revenue=Decimal("700.00"), revenue_ratio=Decimal("0.70"), gross_margin=Decimal("0.85"), source_type="manual", source_url="https://example.com/segment")
            stock_daily = StockDailyHot(stock_code="600276", trade_date=date.today(), open_price=Decimal("45.10"), close_price=Decimal("46.00"), high_price=Decimal("46.50"), low_price=Decimal("44.80"), volume=100000, turnover=Decimal("4600000.00"), source_type="manual")
            stock_daily_old = StockDailyHot(stock_code="600000", trade_date=old_day, open_price=Decimal("12.10"), close_price=Decimal("12.20"), high_price=Decimal("12.30"), low_price=Decimal("11.90"), volume=1000, turnover=Decimal("12000.00"), source_type="manual")

            ann = AnnouncementRawHot(stock_code="600276", title="临床进展公告", publish_date=date.today(), announcement_type="clinical_trial", exchange="SSE", content="创新药临床试验取得积极进展。", source_url="https://example.com/ann", source_type="manual", file_hash="hash-ann")
            ann_old = AnnouncementRawHot(stock_code="600000", title="老公告", publish_date=old_day, announcement_type="general", exchange="SSE", content="一年前公告内容。", source_url="https://example.com/ann-old", source_type="manual", file_hash="hash-ann-old")

            macro = MacroIndicatorHot(indicator_name="医药制造业增加值", period="2026-03", value=Decimal("3.20"), unit="%", source_type="manual", source_url="https://example.com/macro")
            macro_old = MacroIndicatorHot(indicator_name="医药制造业增加值", period="2024-12", value=Decimal("2.10"), unit="%", source_type="manual", source_url="https://example.com/macro-old", created_at=old_dt)

            news = NewsRawHot(news_uid="news-uid-1", title="创新药政策利好", publish_time=datetime.now(timezone.utc), source_name="示例新闻", source_url="https://example.com/news", author_name="记者甲", content="政策支持创新药发展。", news_type="policy_news", language="zh", file_hash="hash-news")
            news_old = NewsRawHot(news_uid="news-uid-old", title="旧新闻", publish_time=old_dt, source_name="示例新闻", source_url="https://example.com/news-old", author_name="记者乙", content="一年前新闻。", news_type="industry_news", language="zh", file_hash="hash-news-old")

            db.add_all([user, company, company_old, profile, industry1, industry2, industry_map, income, income_old, balance, cashflow, note, segment, stock_daily, stock_daily_old, ann, ann_old, macro, macro_old, news, news_old, *metrics])
            db.flush()

            ann_struct = AnnouncementStructuredHot(announcement_id=ann.id, stock_code="600276", category="clinical_trial", summary_text="临床推进", key_fields_json={"phase": "III"}, signal_type="opportunity", risk_level="low")
            drug = DrugApprovalHot(stock_code="600276", drug_name="创新药A", approval_type="上市申请", approval_date=date.today(), indication="肿瘤", drug_stage="NDA", is_innovative_drug=1, review_status="受理", market_scope="中国", source_announcement_id=ann.id, source_type="manual", source_url="https://example.com/drug")
            trial = ClinicalTrialEventHot(stock_code="600276", drug_name="创新药A", trial_phase="III期", event_type="入组完成", event_date=date.today(), indication="肿瘤", summary_text="III期入组完成", source_announcement_id=ann.id, source_type="manual", source_url="https://example.com/trial")
            procurement = CentralizedProcurementEventHot(stock_code="600276", drug_name="仿制药B", procurement_round="第十批", bid_result="中标", price_change_ratio=Decimal("-0.12"), event_date=date.today(), impact_summary="价格承压", source_announcement_id=ann.id, source_type="manual", source_url="https://example.com/proc")
            risk = RegulatoryRiskEventHot(stock_code="600276", risk_type="合规检查", event_date=date.today(), risk_level="medium", summary_text="监管检查", source_announcement_id=ann.id, source_type="manual", source_url="https://example.com/risk")

            news_struct = NewsStructuredHot(news_id=news.id, topic_category="policy", summary_text="政策利好创新药", keywords_json=["创新药"], signal_type="positive", impact_level="high", impact_horizon="medium", sentiment_label="positive", confidence_score=Decimal("0.90"))
            news_industry = NewsIndustryMapHot(news_id=news.id, industry_code="IND001", impact_direction="positive", impact_strength=Decimal("0.85"), reason_text="政策支持")
            news_company = NewsCompanyMapHot(news_id=news.id, stock_code="600276", impact_direction="positive", impact_strength=Decimal("0.82"), reason_text="公司受益")
            industry_impact = IndustryImpactEventHot(industry_code="IND001", source_news_id=news.id, event_name="policy", impact_direction="positive", impact_level="high", impact_horizon="medium", summary_text="行业受益", event_date=date.today())

            db.add_all([ann_struct, drug, trial, procurement, risk, news_struct, news_industry, news_company, industry_impact])
            db.commit()
    return SessionLocal


@pytest.fixture()
def services(session_factory):
    ctx = ServiceContext(session_factory=session_factory, cache=None, vector_store=FakeVectorStore())
    company = CompanyService(ctx=ctx)
    retrieval = RetrievalService(ctx=ctx, company_service=company)
    cache = CacheService(ctx=ctx)
    company_write = CompanyWriteService(ctx=ctx)
    financial_write = FinancialWriteService(ctx=ctx)
    announcement_write = AnnouncementWriteService(ctx=ctx)
    macro_write = MacroWriteService(ctx=ctx)
    news_write = NewsWriteService(ctx=ctx)
    maintenance = MaintenanceService(ctx=ctx)
    ingest = IngestGatewayService(
        ctx=ctx,
        company_write=company_write,
        financial_write=financial_write,
        announcement_write=announcement_write,
        macro_write=macro_write,
        news_write=news_write,
    )
    return {
        "company": company,
        "financial": FinancialService(ctx=ctx, company_service=company),
        "announcement": AnnouncementService(ctx=ctx, company_service=company),
        "news": NewsService(ctx=ctx, company_service=company, retrieval_service=retrieval),
        "macro": MacroService(ctx=ctx),
        "retrieval": retrieval,
        "chat": ChatService(ctx=ctx, company_service=company, cache_service=cache),
        "cache": cache,
        "company_write": company_write,
        "financial_write": financial_write,
        "announcement_write": announcement_write,
        "macro_write": macro_write,
        "news_write": news_write,
        "maintenance": maintenance,
        "ingest": ingest,
        "session_factory": session_factory,
    }
