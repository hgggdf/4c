from __future__ import annotations

from crawler.clients.http_client import load_sample_json
from crawler.pipelines.announcement_pipeline import build_announcement_package_payload
from crawler.pipelines.financial_pipeline import build_financial_package_payload
from crawler.pipelines.macro_pipeline import build_macro_write_payload
from crawler.pipelines.research_report_pipeline import build_research_report_news_package_payload
from crawler.scripts.run_announcement_ingest import run_ingest as run_announcement_ingest
from crawler.scripts.run_financial_ingest import run_ingest as run_financial_ingest
from crawler.scripts.run_macro_ingest import run_ingest as run_macro_ingest
from crawler.scripts.run_research_report_ingest import run_ingest as run_research_report_ingest


def test_financial_pipeline_builds_complete_payload_from_sample_wrapper() -> None:
    sample = load_sample_json("financial_sample.json")

    payload = build_financial_package_payload(sample, "600276", sync_vector_index=False)

    assert len(payload["income_statements"]) == 2
    assert len(payload["balance_sheets"]) == 2
    assert len(payload["cashflow_statements"]) == 2
    assert len(payload["financial_metrics"]) >= 4
    assert len(payload["financial_notes"]) == 1
    assert len(payload["business_segments"]) == 2
    assert len(payload["stock_daily"]) == 2
    assert payload["sync_vector_index"] is False


def test_announcement_pipeline_dedupes_and_prefers_official_source() -> None:
    dataset = {
        "success": True,
        "source": "sse",
        "strategy": "requests/json",
        "items": [
            {
                "stock_code": "600276",
                "title": "恒瑞医药测试公告",
                "publish_date": "2026-04-21",
                "announcement_type": "公告",
                "exchange": "SSE",
                "content": "mirror",
                "source_url": "https://eastmoney.example.com/a",
                "source_type": "eastmoney_announcement_api",
            },
            {
                "stock_code": "600276",
                "title": "恒瑞医药测试公告",
                "publish_date": "2026-04-21",
                "announcement_type": "公告",
                "exchange": "SSE",
                "content": "official content",
                "source_url": "https://sse.example.com/a",
                "source_type": "sse_announcement_api",
            },
        ],
    }

    payload = build_announcement_package_payload(dataset, "600276", sync_vector_index=False)

    assert len(payload["raw_announcements"]) == 1
    item = payload["raw_announcements"][0]
    assert item["source_type"] == "sse_announcement_api"
    assert item["source_url"] == "https://sse.example.com/a"
    assert item["content"] == "official content"


def test_research_report_pipeline_builds_news_payload_from_sample() -> None:
    sample = load_sample_json("research_report_sample.json")

    payload = build_research_report_news_package_payload(sample, sync_vector_index=False)

    assert len(payload["news_raw"]) == 4
    news_types = {item["news_type"] for item in payload["news_raw"]}
    assert "industry_research_report" in news_types
    assert "company_research_report" in news_types
    assert payload["sync_vector_index"] is False


def test_macro_pipeline_accepts_standard_result_wrapper() -> None:
    sample = load_sample_json("macro_sample.json")
    wrapper = {
        "success": True,
        "source": "local-sample",
        "strategy": "fallback",
        "data": sample,
    }

    payload = build_macro_write_payload(wrapper)

    assert len(payload["items"]) == 9
    assert {item["source_type"] for item in payload["items"]} == {"local-sample"}


def test_dry_run_fallback_scripts_return_non_empty_results() -> None:
    financial = run_financial_ingest(
        "600276",
        base_url="http://127.0.0.1:8000",
        sync_vector_index=False,
        timeout=5,
        source_mode="fallback",
        strategy="fallback",
        history_days=30,
        dry_run=True,
    )
    announcement = run_announcement_ingest(
        "600276",
        base_url="http://127.0.0.1:8000",
        sync_vector_index=False,
        timeout=5,
        source_mode="fallback",
        strategy="fallback",
        limit=5,
        begin_date=None,
        end_date=None,
        announcement_type="全部",
        dry_run=True,
    )
    macro = run_macro_ingest(
        None,
        base_url="http://127.0.0.1:8000",
        dbcode="hgyd",
        input_file=None,
        limit_per_indicator=3,
        timeout=5,
        source_mode="fallback",
        strategy="fallback",
        dry_run=True,
    )
    research = run_research_report_ingest(
        ["600276"],
        keyword="医药",
        stock_limit=2,
        industry_limit=2,
        base_url="http://127.0.0.1:8000",
        timeout=5,
        source_mode="fallback",
        strategy="fallback",
        sync_vector_index=False,
        dry_run=True,
    )

    assert financial["success"] is True and financial["fetched_count"] > 0 and financial["written_count"] == 0
    assert announcement["success"] is True and announcement["fetched_count"] > 0 and announcement["written_count"] == 0
    assert macro["success"] is True and macro["fetched_count"] > 0 and macro["written_count"] == 0
    assert research["success"] is True and research["fetched_count"] > 0 and research["written_count"] == 0