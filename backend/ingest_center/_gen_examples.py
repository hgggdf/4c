import json
import hashlib
import os

EXAMPLES_DIR = "ingest_center/examples"

def write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def compute_sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def make_manifest(data_category: str, job_id: str, staging_path: str, raw_path: str, quality_path: str, sha256: str, endpoint: str, target_table: str, ingest_package: str, ingest_field: str) -> dict:
    return {
        "spec_version": "1.0",
        "job_id": job_id,
        "created_at": "2026-04-23T14:00:00+08:00",
        "producer": {
            "system": "OpenClaw",
            "module": f"{data_category}_extractor",
            "run_id": "run_20260423_001"
        },
        "data_category": data_category,
        "time_window": {
            "begin_date": "2025-12-31",
            "end_date": "2025-12-31"
        },
        "target": {
            "endpoint": endpoint,
            "ingest_package": ingest_package,
            "ingest_field": ingest_field,
            "target_table": target_table
        },
        "files": {
            "raw_path": raw_path,
            "staging_path": staging_path,
            "quality_report_path": quality_path
        },
        "record_stats": {
            "raw_count": 1,
            "staging_count": 1,
            "expected_write_count": 1
        },
        "checksum": {
            "staging_sha256": sha256
        },
        "status": "ready"
    }

def make_quality_report(data_category: str) -> dict:
    return {
        "data_category": data_category,
        "quality_score": 1.0,
        "checks": {"format": {"passed": True, "missing_fields": []}},
        "warnings": [],
        "generated_at": "2026-04-23T14:00:00+08:00"
    }

# ------------------------------------------------------------------
# company
# ------------------------------------------------------------------
company_staging = {
    "payload": {
        "company_master": {
            "stock_code": "600001",
            "stock_name": "Test Company",
            "exchange": "SH"
        }
    }
}
write_json(f"{EXAMPLES_DIR}/company/staging.json", company_staging)
company_sha256 = compute_sha256(f"{EXAMPLES_DIR}/company/staging.json")
write_json(f"{EXAMPLES_DIR}/company/quality_report.json", make_quality_report("company"))
write_json(f"{EXAMPLES_DIR}/company/manifest.json", make_manifest(
    "company", "example_company_001",
    "backend/ingest_center/examples/company/staging.json",
    "backend/ingest_center/examples/company/raw.json",
    "backend/ingest_center/examples/company/quality_report.json",
    company_sha256,
    "/api/ingest/company-package",
    "company_master",
    "company_package",
    "company_master"
))
print(f"company sha256: {company_sha256}")

# ------------------------------------------------------------------
# stock_daily
# ------------------------------------------------------------------
stock_staging = {
    "payload": {
        "stock_daily": [
            {
                "stock_code": "600001",
                "trade_date": "2025-12-31",
                "open_price": 10.0,
                "close_price": 11.0,
                "high_price": 12.0,
                "low_price": 9.0
            }
        ]
    }
}
write_json(f"{EXAMPLES_DIR}/stock_daily/staging.json", stock_staging)
stock_sha256 = compute_sha256(f"{EXAMPLES_DIR}/stock_daily/staging.json")
write_json(f"{EXAMPLES_DIR}/stock_daily/quality_report.json", make_quality_report("stock_daily"))
write_json(f"{EXAMPLES_DIR}/stock_daily/manifest.json", make_manifest(
    "stock_daily", "example_stock_daily_001",
    "backend/ingest_center/examples/stock_daily/staging.json",
    "backend/ingest_center/examples/stock_daily/raw.json",
    "backend/ingest_center/examples/stock_daily/quality_report.json",
    stock_sha256,
    "/api/ingest/financial-package",
    "stock_daily_hot",
    "financial_package",
    "stock_daily"
))
print(f"stock_daily sha256: {stock_sha256}")

# ------------------------------------------------------------------
# announcement_raw
# ------------------------------------------------------------------
ann_staging = {
    "payload": {
        "raw_announcements": [
            {
                "stock_code": "600001",
                "title": "Test Announcement",
                "publish_date": "2025-12-31",
                "content": "This is a test announcement content.",
                "source_url": "https://example.com/announcement"
            }
        ]
    }
}
write_json(f"{EXAMPLES_DIR}/announcement_raw/staging.json", ann_staging)
ann_sha256 = compute_sha256(f"{EXAMPLES_DIR}/announcement_raw/staging.json")
write_json(f"{EXAMPLES_DIR}/announcement_raw/quality_report.json", make_quality_report("announcement_raw"))
write_json(f"{EXAMPLES_DIR}/announcement_raw/manifest.json", make_manifest(
    "announcement_raw", "example_announcement_001",
    "backend/ingest_center/examples/announcement_raw/staging.json",
    "backend/ingest_center/examples/announcement_raw/raw.json",
    "backend/ingest_center/examples/announcement_raw/quality_report.json",
    ann_sha256,
    "/api/ingest/announcement-package",
    "announcement_raw",
    "announcement_package",
    "raw_announcements"
))
print(f"announcement_raw sha256: {ann_sha256}")

# ------------------------------------------------------------------
# research_report
# ------------------------------------------------------------------
rr_staging = {
    "payload": {
        "news_raw": [
            {
                "title": "Test Research Report",
                "publish_time": "2025-12-31T10:00:00",
                "content": "This is a test research report content.",
                "news_type": "research",
                "source_url": "https://example.com/report"
            }
        ]
    }
}
write_json(f"{EXAMPLES_DIR}/research_report/staging.json", rr_staging)
rr_sha256 = compute_sha256(f"{EXAMPLES_DIR}/research_report/staging.json")
write_json(f"{EXAMPLES_DIR}/research_report/quality_report.json", make_quality_report("research_report"))
write_json(f"{EXAMPLES_DIR}/research_report/manifest.json", make_manifest(
    "research_report", "example_research_report_001",
    "backend/ingest_center/examples/research_report/staging.json",
    "backend/ingest_center/examples/research_report/raw.json",
    "backend/ingest_center/examples/research_report/quality_report.json",
    rr_sha256,
    "/api/ingest/news-package",
    "news_raw",
    "news_package",
    "news_raw"
))
print(f"research_report sha256: {rr_sha256}")

# ------------------------------------------------------------------
# macro
# ------------------------------------------------------------------
macro_staging = {
    "records": [
        {
            "indicator_name": "GDP",
            "period": "2025-Q4",
            "value": 100.0,
            "unit": "trillion",
            "source_type": "test",
            "source_url": "https://example.com/macro"
        }
    ]
}
write_json(f"{EXAMPLES_DIR}/macro/staging.json", macro_staging)
macro_sha256 = compute_sha256(f"{EXAMPLES_DIR}/macro/staging.json")
write_json(f"{EXAMPLES_DIR}/macro/quality_report.json", make_quality_report("macro"))
write_json(f"{EXAMPLES_DIR}/macro/manifest.json", make_manifest(
    "macro", "example_macro_001",
    "backend/ingest_center/examples/macro/staging.json",
    "backend/ingest_center/examples/macro/raw.json",
    "backend/ingest_center/examples/macro/quality_report.json",
    macro_sha256,
    "/api/macro-write/macro-indicators",
    "macro_indicator",
    "macro_indicators",
    "items"
))
print(f"macro sha256: {macro_sha256}")

# ------------------------------------------------------------------
# patent
# ------------------------------------------------------------------
patent_staging = {
    "records": [
        {
            "patent_id": "CN123456789",
            "title": "Test Patent"
        }
    ]
}
write_json(f"{EXAMPLES_DIR}/patent/staging.json", patent_staging)
patent_sha256 = compute_sha256(f"{EXAMPLES_DIR}/patent/staging.json")
write_json(f"{EXAMPLES_DIR}/patent/quality_report.json", make_quality_report("patent"))
write_json(f"{EXAMPLES_DIR}/patent/manifest.json", make_manifest(
    "patent", "example_patent_001",
    "backend/ingest_center/examples/patent/staging.json",
    "backend/ingest_center/examples/patent/raw.json",
    "backend/ingest_center/examples/patent/quality_report.json",
    patent_sha256,
    "/api/ingest/patent-package",
    "patent",
    "patent_package",
    "patents"
))
print(f"patent sha256: {patent_sha256}")

print("\nAll example files generated.")
