from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.service import (
    AnnouncementWriteService,
    CompanyWriteService,
    FinancialWriteService,
    IngestGatewayService,
    MacroWriteService,
    MaintenanceService,
    NewsWriteService,
)
from app.service.write_requests import (
    ArchiveHotDataRequest,
    BatchItemsRequest,
    BatchUpsertFinancialRequest,
    BatchUpsertIndustriesRequest,
    IngestAnnouncementPackageRequest,
    IngestCompanyPackageRequest,
    IngestFinancialPackageRequest,
    IngestNewsPackageRequest,
    InvalidateStockCacheRequest,
    RebuildAnnouncementSummaryRequest,
    RebuildDrugPipelineSummaryRequest,
    RebuildFinancialMetricSummaryRequest,
    RebuildIndustryNewsSummaryRequest,
    ReplaceCompanyIndustriesRequest,
    ReplaceNewsCompanyMapRequest,
    ReplaceNewsIndustryMapRequest,
    UpsertCompanyMasterRequest,
    UpsertCompanyProfileRequest,
    UpsertWatchlistRequest,
)


EXPECTED_PUBLIC_METHODS = {
    CompanyWriteService: {"upsert_company_master", "batch_upsert_company_master", "upsert_company_profile", "batch_upsert_industries", "replace_company_industries", "upsert_watchlist"},
    FinancialWriteService: {"batch_upsert_income_statements", "batch_upsert_balance_sheets", "batch_upsert_cashflow_statements", "batch_upsert_financial_metrics", "batch_upsert_financial_notes", "batch_upsert_business_segments", "batch_upsert_stock_daily"},
    AnnouncementWriteService: {"batch_upsert_raw_announcements", "batch_upsert_structured_announcements", "batch_upsert_drug_approvals", "batch_upsert_clinical_trials", "batch_upsert_procurement_events", "batch_upsert_regulatory_risks"},
    MacroWriteService: {"batch_upsert_macro_indicators"},
    NewsWriteService: {"batch_upsert_news_raw", "batch_upsert_news_structured", "replace_news_industry_map", "replace_news_company_map", "batch_upsert_industry_impact_events"},
    MaintenanceService: {"archive_hot_data", "rebuild_financial_metric_summary_yearly", "rebuild_announcement_summary_monthly", "rebuild_drug_pipeline_summary_yearly", "rebuild_industry_news_summary_monthly", "invalidate_stock_related_caches"},
    IngestGatewayService: {"ingest_company_package", "ingest_financial_package", "ingest_announcement_package", "ingest_news_package"},
}


def test_write_service_public_methods_complete():
    for cls, expected in EXPECTED_PUBLIC_METHODS.items():
        actual = {name for name, obj in cls.__dict__.items() if callable(obj) and not name.startswith("_")}
        assert actual == expected


def test_company_write_service_all_methods(services, monkeypatch):
    company_write = services["company_write"]

    master = company_write.upsert_company_master(
        UpsertCompanyMasterRequest(
            stock_code="600001",
            stock_name="测试医药一号",
            full_name="测试医药一号股份有限公司",
            exchange="SSE",
            industry_level1="医药生物",
            industry_level2="创新药",
            alias_json=["测试一号"],
            source_type="manual",
            source_url="https://example.com/600001",
        )
    )
    assert master.success is True and master.data["stock_code"] == "600001"

    batch_master = company_write.batch_upsert_company_master(
        BatchUpsertIndustriesRequest(
            items=[
                {"stock_code": "600002", "stock_name": "测试医药二号", "industry_level1": "医药生物", "industry_level2": "CXO", "source_type": "manual"},
                {"stock_code": "600003", "stock_name": "测试医药三号", "industry_level1": "医药生物", "industry_level2": "器械", "source_type": "manual"},
            ]
        )
    )
    assert batch_master.success is True and batch_master.data["created_count"] >= 2

    industries = company_write.batch_upsert_industries(
        BatchUpsertIndustriesRequest(items=[
            {"industry_code": "IND003", "industry_name": "CXO", "industry_level": 1},
            {"industry_code": "IND004", "industry_name": "器械", "industry_level": 1},
        ])
    )
    assert industries.success is True and set(industries.data["industry_codes"]) >= {"IND003", "IND004"}

    import app.knowledge.sync as kg_sync
    monkeypatch.setattr(kg_sync, "sync_company_profiles_by_ids", lambda db, source_ids: len(source_ids))
    profile = company_write.upsert_company_profile(
        UpsertCompanyProfileRequest(stock_code="600001", business_summary="聚焦肿瘤创新药", market_position="成长型公司", sync_vector_index=True)
    )
    assert profile.success is True and profile.data["sync_status"] in {"synced", "skipped"}

    mappings = company_write.replace_company_industries(
        ReplaceCompanyIndustriesRequest(stock_code="600001", items=[{"industry_code": "IND001", "is_primary": 1}, {"industry_code": "IND003", "is_primary": 0}])
    )
    assert mappings.success is True and mappings.data["mapping_count"] == 2

    watch = company_write.upsert_watchlist(UpsertWatchlistRequest(user_id=1, stock_code="600001", remark="重点跟踪", tags_json=["新股", "创新药"], alert_enabled=1))
    assert watch.success is True and watch.data["stock_code"] == "600001"


def test_financial_write_service_all_methods(services, monkeypatch):
    financial_write = services["financial_write"]
    import app.knowledge.sync as kg_sync
    monkeypatch.setattr(kg_sync, "sync_financial_notes_by_ids", lambda db, source_ids, is_hot=True: len(source_ids))

    assert financial_write.batch_upsert_income_statements(BatchUpsertFinancialRequest(items=[{"stock_code": "600001", "report_date": date(2026, 3, 31), "fiscal_year": 2026, "report_type": "q1", "revenue": 100, "net_profit": 10, "source_type": "manual"}])).success is True
    assert financial_write.batch_upsert_balance_sheets(BatchUpsertFinancialRequest(items=[{"stock_code": "600001", "report_date": date(2026, 3, 31), "fiscal_year": 2026, "report_type": "q1", "total_assets": 500, "total_liabilities": 100, "source_type": "manual"}])).success is True
    assert financial_write.batch_upsert_cashflow_statements(BatchUpsertFinancialRequest(items=[{"stock_code": "600001", "report_date": date(2026, 3, 31), "fiscal_year": 2026, "report_type": "q1", "operating_cashflow": 30, "free_cashflow": 20, "source_type": "manual"}])).success is True
    assert financial_write.batch_upsert_financial_metrics(BatchUpsertFinancialRequest(items=[{"stock_code": "600001", "report_date": date(2026, 3, 31), "fiscal_year": 2026, "metric_name": "gross_margin", "metric_value": 0.55, "metric_unit": "ratio"}])).success is True
    notes = financial_write.batch_upsert_financial_notes(BatchUpsertFinancialRequest(items=[{"stock_code": "600001", "report_date": date(2026, 3, 31), "note_type": "rd_pipeline", "note_json": {"n": 2}, "note_text": "研发管线更新", "source_type": "manual"}], sync_vector_index=True))
    assert notes.success is True and notes.data["sync_status"] in {"synced", "skipped"}
    assert financial_write.batch_upsert_business_segments(BatchUpsertFinancialRequest(items=[{"stock_code": "600001", "report_date": date(2026, 3, 31), "segment_name": "创新药", "segment_type": "drug", "revenue": 80, "revenue_ratio": 0.8, "gross_margin": 0.7, "source_type": "manual"}])).success is True
    assert financial_write.batch_upsert_stock_daily(BatchUpsertFinancialRequest(items=[{"stock_code": "600001", "trade_date": date(2026, 4, 21), "open_price": 10.1, "close_price": 10.5, "high_price": 10.6, "low_price": 10.0, "volume": 1000, "turnover": 10500, "source_type": "manual"}])).success is True


def test_announcement_write_service_all_methods(services, monkeypatch):
    announcement_write = services["announcement_write"]
    import app.knowledge.sync as kg_sync
    monkeypatch.setattr(kg_sync, "sync_announcements_by_ids", lambda db, source_ids, is_hot=True: len(source_ids))

    raw = announcement_write.batch_upsert_raw_announcements(BatchItemsRequest(items=[{"stock_code": "600001", "title": "测试公告", "publish_date": date(2026, 4, 21), "announcement_type": "clinical_trial", "exchange": "SSE", "content": "公告正文", "source_type": "manual", "source_url": "https://example.com/ann-600001"}], sync_vector_index=True))
    assert raw.success is True and raw.data["sync_status"] in {"synced", "skipped"}
    ann_id = raw.data["ids"][0]

    assert announcement_write.batch_upsert_structured_announcements(BatchItemsRequest(items=[{"announcement_id": ann_id, "stock_code": "600001", "category": "clinical_trial", "summary_text": "结构化摘要", "signal_type": "opportunity", "risk_level": "low"}])).success is True
    assert announcement_write.batch_upsert_drug_approvals(BatchItemsRequest(items=[{"stock_code": "600001", "drug_name": "药物X", "approval_type": "IND", "approval_date": date(2026, 4, 21), "indication": "肿瘤", "drug_stage": "IND", "is_innovative_drug": 1, "source_announcement_id": ann_id}])).success is True
    assert announcement_write.batch_upsert_clinical_trials(BatchItemsRequest(items=[{"stock_code": "600001", "drug_name": "药物X", "trial_phase": "II期", "event_type": "启动", "event_date": date(2026, 4, 21), "indication": "肿瘤", "source_announcement_id": ann_id}])).success is True
    assert announcement_write.batch_upsert_procurement_events(BatchItemsRequest(items=[{"stock_code": "600001", "drug_name": "药物Y", "procurement_round": "第九批", "bid_result": "中标", "event_date": date(2026, 4, 21), "source_announcement_id": ann_id}])).success is True
    assert announcement_write.batch_upsert_regulatory_risks(BatchItemsRequest(items=[{"stock_code": "600001", "risk_type": "合规", "event_date": date(2026, 4, 21), "risk_level": "medium", "source_announcement_id": ann_id}])).success is True


def test_macro_news_write_service_all_methods(services, monkeypatch):
    macro_write = services["macro_write"]
    news_write = services["news_write"]
    import app.knowledge.sync as kg_sync
    monkeypatch.setattr(kg_sync, "sync_news_by_ids", lambda db, source_ids, is_hot=True: len(source_ids))

    assert macro_write.batch_upsert_macro_indicators(BatchItemsRequest(items=[{"indicator_name": "创新药景气度", "period": "2026-04", "value": 5.6, "unit": "%", "source_type": "manual"}])).success is True
    raw = news_write.batch_upsert_news_raw(BatchItemsRequest(items=[{"news_uid": "news-600001", "title": "测试新闻", "publish_time": datetime.now(timezone.utc), "source_name": "测试源", "source_url": "https://example.com/news-600001", "content": "新闻正文", "news_type": "company_news", "language": "zh", "file_hash": "hash-600001"}], sync_vector_index=True))
    assert raw.success is True and raw.data["sync_status"] in {"synced", "skipped"}
    news_id = raw.data["ids"][0]
    assert news_write.batch_upsert_news_structured(BatchItemsRequest(items=[{"news_id": news_id, "topic_category": "company", "summary_text": "结构化新闻", "signal_type": "positive", "impact_level": "medium", "impact_horizon": "short", "sentiment_label": "positive", "confidence_score": 0.9}])).success is True
    assert news_write.replace_news_industry_map(ReplaceNewsIndustryMapRequest(news_id=news_id, items=[{"industry_code": "IND001", "impact_direction": "positive", "impact_strength": 0.8, "reason_text": "利好创新药"}])).success is True
    assert news_write.replace_news_company_map(ReplaceNewsCompanyMapRequest(news_id=news_id, items=[{"stock_code": "600001", "impact_direction": "positive", "impact_strength": 0.7, "reason_text": "公司受益"}])).success is True
    assert news_write.batch_upsert_industry_impact_events(BatchItemsRequest(items=[{"industry_code": "IND001", "source_news_id": news_id, "event_name": "news_event", "impact_direction": "positive", "impact_level": "medium", "impact_horizon": "short", "summary_text": "行业影响", "event_date": date(2026, 4, 21)}])).success is True


def test_maintenance_service_all_methods(services):
    maintenance = services["maintenance"]
    services["cache"].set_query_cache(__import__('app.service.requests', fromlist=['CacheSetQueryRequest']).CacheSetQueryRequest(user_id=1, cache_key='cache:600001', query_text='600001 query', result={'ok': 1}, source_signature='600001', ttl_seconds=60))
    services["cache"].set_hot_data(__import__('app.service.requests', fromlist=['CacheSetHotDataRequest']).CacheSetHotDataRequest(data_type='company', cache_key='summary:600001', value={'ok': 1}, ttl_seconds=60))

    assert maintenance.rebuild_financial_metric_summary_yearly(RebuildFinancialMetricSummaryRequest(stock_code="600276", year=date.today().year)).success is True
    assert maintenance.rebuild_announcement_summary_monthly(RebuildAnnouncementSummaryRequest(stock_code="600276", year_month=date.today().strftime("%Y-%m"))).success is True
    assert maintenance.rebuild_drug_pipeline_summary_yearly(RebuildDrugPipelineSummaryRequest(stock_code="600276", year=date.today().year)).success is True
    assert maintenance.rebuild_industry_news_summary_monthly(RebuildIndustryNewsSummaryRequest(industry_code="IND001", year_month=date.today().strftime("%Y-%m"))).success is True
    invalid = maintenance.invalidate_stock_related_caches(InvalidateStockCacheRequest(stock_code="600001"))
    assert invalid.success is True and invalid.data["stock_code"] == "600001"
    archived = maintenance.archive_hot_data(ArchiveHotDataRequest(cutoff_date=date.today() - timedelta(days=365)))
    assert archived.success is True and archived.data["total_archived"] >= 1


def test_ingest_gateway_service_all_methods(services, monkeypatch):
    ingest = services["ingest"]
    import app.knowledge.sync as kg_sync
    monkeypatch.setattr(kg_sync, "sync_company_profiles_by_ids", lambda db, source_ids: len(source_ids))
    monkeypatch.setattr(kg_sync, "sync_financial_notes_by_ids", lambda db, source_ids, is_hot=True: len(source_ids))
    monkeypatch.setattr(kg_sync, "sync_announcements_by_ids", lambda db, source_ids, is_hot=True: len(source_ids))
    monkeypatch.setattr(kg_sync, "sync_news_by_ids", lambda db, source_ids, is_hot=True: len(source_ids))

    company_pkg = ingest.ingest_company_package(
        IngestCompanyPackageRequest(
            company_master={"stock_code": "600010", "stock_name": "网关公司", "industry_level1": "医药生物", "industry_level2": "创新药", "source_type": "manual"},
            company_profile={"stock_code": "600010", "business_summary": "网关写入公司画像"},
            industries=[{"industry_code": "IND010", "industry_name": "网关行业", "industry_level": 1}],
            company_industries=[{"industry_code": "IND010", "is_primary": 1}],
        )
    )
    assert company_pkg.success is True and company_pkg.data["company_master"]["stock_code"] == "600010"

    financial_pkg = ingest.ingest_financial_package(
        IngestFinancialPackageRequest(
            income_statements=[{"stock_code": "600010", "report_date": date(2026, 3, 31), "fiscal_year": 2026, "report_type": "q1", "revenue": 11}],
            financial_notes=[{"stock_code": "600010", "report_date": date(2026, 3, 31), "note_type": "product_split", "note_text": "产品结构调整"}],
            sync_vector_index=True,
        )
    )
    assert financial_pkg.success is True and financial_pkg.data["financial_notes"]["total"] >= 1

    ann_pkg = ingest.ingest_announcement_package(
        IngestAnnouncementPackageRequest(
            raw_announcements=[{"stock_code": "600010", "title": "网关公告", "publish_date": date(2026, 4, 21), "content": "公告正文", "announcement_type": "general", "exchange": "SSE"}],
            structured_announcements=[],
            sync_vector_index=True,
        )
    )
    assert ann_pkg.success is True and ann_pkg.data["raw_announcements"]["total"] >= 1

    news_pkg = ingest.ingest_news_package(
        IngestNewsPackageRequest(
            macro_indicators=[{"indicator_name": "网关宏观", "period": "2026-04", "value": 1.2}],
            news_raw=[{"news_uid": "gateway-news-1", "title": "网关新闻", "publish_time": datetime.now(timezone.utc), "source_name": "网关", "content": "新闻", "news_type": "company_news"}],
            sync_vector_index=True,
        )
    )
    assert news_pkg.success is True and news_pkg.data["news_raw"]["total"] >= 1