from __future__ import annotations

from app.service import (
    AnnouncementService,
    CacheService,
    ChatService,
    CompanyService,
    FinancialService,
    MacroService,
    NewsService,
    RetrievalService,
)
from app.service.requests import (
    CacheGetHotDataRequest,
    CacheGetSessionContextRequest,
    CacheInvalidateRequest,
    CacheQueryRequest,
    CacheSetHotDataRequest,
    CacheSetQueryRequest,
    CacheSetSessionContextRequest,
    ChatAppendMessageRequest,
    ChatCreateSessionRequest,
    ChatListSessionsRequest,
    ChatSessionRequest,
    ChatUpdateCurrentStockRequest,
    FinancialMetricsRequest,
    FinancialSummaryRequest,
    ImpactSummaryRequest,
    IndustryDaysRequest,
    MacroIndicatorRequest,
    MacroListRequest,
    MacroSummaryRequest,
    NewsRawRequest,
    NewsStructuredRequest,
    RebuildEmbeddingsRequest,
    SearchRequest,
    StockCodeDaysRequest,
    StockCodeLimitRequest,
)


EXPECTED_PUBLIC_METHODS = {
    CompanyService: {"get_company_basic_info", "get_company_profile", "get_company_industries", "get_company_overview", "resolve_company", "ensure_company_exists"},
    FinancialService: {"get_income_statements", "get_balance_sheets", "get_cashflow_statements", "get_financial_metrics", "get_business_segments", "get_financial_summary"},
    AnnouncementService: {"get_raw_announcements", "get_structured_announcements", "get_drug_approvals", "get_clinical_trials", "get_procurement_events", "get_regulatory_risks", "get_company_event_summary"},
    NewsService: {"get_news_raw", "get_news_by_company", "get_news_by_industry", "get_news_structured", "get_company_news_impact", "get_industry_news_impact", "get_news_impact_summary"},
    MacroService: {"get_macro_indicator", "list_macro_indicators", "get_macro_summary"},
    RetrievalService: {"search_announcements", "search_financial_notes", "search_news", "search_reports", "search_policies", "search_text_evidence", "search_announcement_evidence", "search_financial_note_evidence", "search_news_evidence", "rebuild_document_embeddings", "delete_document_embeddings"},
    ChatService: {"get_session", "list_sessions", "list_messages", "get_current_context", "create_session", "append_user_message", "append_assistant_message", "update_current_stock"},
    CacheService: {"get_query_cache", "set_query_cache", "get_session_context", "set_session_context", "get_hot_data", "set_hot_data", "invalidate"},
}


def test_read_service_public_methods_complete():
    for cls, expected in EXPECTED_PUBLIC_METHODS.items():
        actual = {name for name, obj in cls.__dict__.items() if callable(obj) and not name.startswith("_")}
        assert actual == expected


def test_company_service_all_methods(services):
    company = services["company"]
    assert company.get_company_basic_info("600276").success is True
    assert company.get_company_profile("600276").data["business_summary"]
    assert company.get_company_industries("600276").data[0]["industry_code"] == "IND001"
    assert company.get_company_overview("600276").data["profile"]["business_summary"]
    assert company.resolve_company("请分析恒瑞医药").data[0]["stock_code"] == "600276"
    assert company.ensure_company_exists("600276").data is True


def test_financial_service_all_methods(services):
    financial = services["financial"]
    assert financial.get_income_statements(StockCodeLimitRequest(stock_code="600276", limit=4)).success is True
    assert financial.get_balance_sheets(StockCodeLimitRequest(stock_code="600276", limit=4)).data[0]["total_assets"] > 0
    assert financial.get_cashflow_statements(StockCodeLimitRequest(stock_code="600276", limit=4)).data[0]["free_cashflow"] > 0
    assert financial.get_financial_metrics(FinancialMetricsRequest(stock_code="600276", limit=10, metric_names=["gross_margin", "rd_ratio"])).data[0]["metric_name"] in {"gross_margin", "rd_ratio"}
    assert financial.get_business_segments(StockCodeLimitRequest(stock_code="600276", limit=10)).data[0]["segment_name"] == "抗肿瘤药"
    summary = financial.get_financial_summary(FinancialSummaryRequest(stock_code="600276", period_count=4))
    assert summary.success is True
    assert summary.data["latest_income"]["stock_code"] == "600276"


def test_announcement_service_all_methods(services):
    announcement = services["announcement"]
    assert announcement.get_raw_announcements(StockCodeDaysRequest(stock_code="600276", days=365)).data[0]["title"] == "临床进展公告"
    assert announcement.get_structured_announcements(StockCodeDaysRequest(stock_code="600276", days=365)).data[0]["category"] == "clinical_trial"
    assert announcement.get_drug_approvals(StockCodeDaysRequest(stock_code="600276", days=365)).data[0]["drug_name"] == "创新药A"
    assert announcement.get_clinical_trials(StockCodeDaysRequest(stock_code="600276", days=365)).data[0]["trial_phase"] == "III期"
    assert announcement.get_procurement_events(StockCodeDaysRequest(stock_code="600276", days=365)).data[0]["bid_result"] == "中标"
    assert announcement.get_regulatory_risks(StockCodeDaysRequest(stock_code="600276", days=365)).data[0]["risk_type"] == "合规检查"
    summary = announcement.get_company_event_summary(StockCodeDaysRequest(stock_code="600276", days=365))
    assert summary.success is True
    assert summary.data["counts_by_category"]["clinical_trial"] >= 1


def test_news_service_all_methods(services):
    news = services["news"]
    assert news.get_news_raw(NewsRawRequest(days=30)).data[0]["title"] == "创新药政策利好"
    assert news.get_news_by_company(StockCodeDaysRequest(stock_code="600276", days=30)).data[0]["impact_direction"] == "positive"
    assert news.get_news_by_industry(IndustryDaysRequest(industry_code="IND001", days=30)).data[0]["industry_code"] == "IND001"
    assert news.get_news_structured(NewsStructuredRequest(days=30)).data[0]["topic_category"] == "policy"
    assert news.get_company_news_impact(StockCodeDaysRequest(stock_code="600276", days=30)).data["direction_counts"]["positive"] >= 1
    industry = news.get_industry_news_impact(IndustryDaysRequest(industry_code="IND001", days=30))
    assert industry.data["impact_events"][0]["event_type"] == "policy"
    summary = news.get_news_impact_summary(ImpactSummaryRequest(days=30))
    assert summary.data["sentiment_counts"]["positive"] >= 1


def test_macro_chat_cache_retrieval_all_methods(services, monkeypatch):
    macro = services["macro"]
    chat = services["chat"]
    cache = services["cache"]
    retrieval = services["retrieval"]

    assert macro.get_macro_indicator(MacroIndicatorRequest(indicator_name="医药制造业增加值")).data["indicator_name"] == "医药制造业增加值"
    assert macro.list_macro_indicators(MacroListRequest(indicator_names=["医药制造业增加值"], periods=["2026-03"])).data[0]["period"] == "2026-03"
    assert "医药制造业增加值" in macro.get_macro_summary(MacroSummaryRequest(indicator_names=["医药制造业增加值"], recent_n=3)).data["series"]

    created = chat.create_session(ChatCreateSessionRequest(user_id=1, session_title="read-test"))
    session_id = created.data["id"]
    assert chat.get_session(ChatSessionRequest(session_id=session_id)).data["id"] == session_id
    assert any(s["id"] == session_id for s in chat.list_sessions(ChatListSessionsRequest(user_id=1, limit=50)).data)
    assert chat.get_current_context(ChatSessionRequest(session_id=session_id)).data["context_json"]["current_stock_code"] is None
    assert chat.append_user_message(ChatAppendMessageRequest(session_id=session_id, content="分析恒瑞", stock_code="600276")).data["role"] == "user"
    assert chat.append_assistant_message(ChatAppendMessageRequest(session_id=session_id, content="好的")).data["role"] == "assistant"
    assert len(chat.list_messages(ChatSessionRequest(session_id=session_id)).data) == 2
    assert chat.update_current_stock(ChatUpdateCurrentStockRequest(session_id=session_id, stock_code="600276")).data["current_stock_code"] == "600276"

    cache_key = "pytest:read:query"
    assert cache.set_query_cache(CacheSetQueryRequest(user_id=1, cache_key=cache_key, query_text="test", result={"x": 1}, ttl_seconds=60)).data["cache_key"] == cache_key
    assert cache.get_query_cache(CacheQueryRequest(cache_key=cache_key)).data["result_json"]["x"] == 1
    assert cache.set_session_context(CacheSetSessionContextRequest(session_id=session_id, user_id=1, context={"k": "v"}, ttl_seconds=60)).data["context_json"]["k"] == "v"
    assert cache.get_session_context(CacheGetSessionContextRequest(session_id=session_id)).data["context_json"]["k"] == "v"
    assert cache.set_hot_data(CacheSetHotDataRequest(data_type="macro", cache_key="pytest:hot", value={"v": 2}, ttl_seconds=60)).data["value_json"]["v"] == 2
    assert cache.get_hot_data(CacheGetHotDataRequest(data_type="macro", cache_key="pytest:hot")).data["value_json"]["v"] == 2
    assert cache.invalidate(CacheInvalidateRequest(cache_key="pytest:hot")).success is True

    assert retrieval.search_announcements(SearchRequest(query="恒瑞公告", stock_code="600276", top_k=5)).data["items"][0]["metadata"]["doc_type"] == "announcement"
    assert retrieval.search_financial_notes(SearchRequest(query="研发投入", stock_code="600276", top_k=5)).data["items"][0]["metadata"]["doc_type"] == "financial_note"
    assert retrieval.search_news(SearchRequest(query="政策新闻", stock_code="600276", top_k=5)).data["items"][0]["metadata"]["doc_type"] == "news"
    assert retrieval.search_reports(SearchRequest(query="研报", stock_code="600276", top_k=5)).success is True
    assert retrieval.search_policies(SearchRequest(query="政策", industry_code="IND001", top_k=5)).success is True
    assert retrieval.search_text_evidence(SearchRequest(query="总结恒瑞进展", doc_types=["announcement", "financial_note"], top_k=5)).success is True
    assert retrieval.search_announcement_evidence(SearchRequest(query="公告", stock_code="600276", top_k=5)).success is True
    assert retrieval.search_financial_note_evidence(SearchRequest(query="附注", stock_code="600276", top_k=5)).success is True
    assert retrieval.search_news_evidence(SearchRequest(query="新闻", stock_code="600276", top_k=5)).success is True

    import app.knowledge.sync as kg_sync

    monkeypatch.setattr(kg_sync, "sync_announcements_by_ids", lambda db, source_ids, is_hot=True: len(source_ids))
    rebuilt = retrieval.rebuild_document_embeddings(RebuildEmbeddingsRequest(doc_type="announcement", source_ids=[1, 2]))
    assert rebuilt.success is True and rebuilt.data["reindexed_chunks"] == 2
    deleted = retrieval.delete_document_embeddings(RebuildEmbeddingsRequest(doc_type="announcement", source_ids=[1]))
    assert deleted.success is True and deleted.data["deleted_chunks"] >= 0