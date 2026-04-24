import json
import hashlib
import os

STOCK_CODE = "600000"
REPORT_DATE = "2025-12-31"
REPORT_TYPE = "annual"
FISCAL_YEAR = 2025

# ------------------------------------------------------------------
# 1. staging
# ------------------------------------------------------------------
staging = {
    "payload": {
        "income_statements": [
            {
                "stock_code": STOCK_CODE,
                "report_date": REPORT_DATE,
                "fiscal_year": FISCAL_YEAR,
                "report_type": REPORT_TYPE,
                "revenue": 5000000000.00,
                "operating_cost": 3000000000.00,
                "gross_profit": 2000000000.00,
                "selling_expense": 500000000.00,
                "admin_expense": 300000000.00,
                "rd_expense": 200000000.00,
                "operating_profit": 1000000000.00,
                "net_profit": 850000000.00,
                "net_profit_deducted": 820000000.00,
                "eps": 2.50,
                "source_type": "manual_test",
                "source_url": "https://test.example.com/financial"
            }
        ],
        "balance_sheets": [
            {
                "stock_code": STOCK_CODE,
                "report_date": REPORT_DATE,
                "fiscal_year": FISCAL_YEAR,
                "report_type": REPORT_TYPE,
                "total_assets": 50000000000.00,
                "total_liabilities": 30000000000.00,
                "accounts_receivable": 5000000000.00,
                "inventory": 3000000000.00,
                "cash": 8000000000.00,
                "equity": 20000000000.00,
                "goodwill": 1000000000.00,
                "source_type": "manual_test",
                "source_url": "https://test.example.com/financial"
            }
        ],
        "cashflow_statements": [
            {
                "stock_code": STOCK_CODE,
                "report_date": REPORT_DATE,
                "fiscal_year": FISCAL_YEAR,
                "report_type": REPORT_TYPE,
                "operating_cashflow": 1200000000.00,
                "investing_cashflow": -500000000.00,
                "financing_cashflow": -300000000.00,
                "free_cashflow": 900000000.00,
                "source_type": "manual_test",
                "source_url": "https://test.example.com/financial"
            }
        ],
        "financial_metrics": [
            {
                "stock_code": STOCK_CODE,
                "report_date": REPORT_DATE,
                "fiscal_year": FISCAL_YEAR,
                "metric_name": "ROE",
                "metric_value": 0.1523,
                "metric_unit": "%",
                "calc_method": "net_profit / equity",
                "source_ref_json": {"page": 45, "table": "financial_metrics"}
            },
            {
                "stock_code": STOCK_CODE,
                "report_date": REPORT_DATE,
                "fiscal_year": FISCAL_YEAR,
                "metric_name": "debt_to_asset_ratio",
                "metric_value": 0.60,
                "metric_unit": "%",
                "calc_method": "total_liabilities / total_assets",
                "source_ref_json": {"page": 32, "table": "balance_sheet"}
            }
        ],
        "financial_notes": [
            {
                "stock_code": STOCK_CODE,
                "report_date": REPORT_DATE,
                "note_type": "accounting_policy_change",
                "note_json": {"change_item": "revenue_recognition", "effective_date": "2025-01-01"},
                "note_text": "Adjusted according to new revenue recognition standards for the current year.",
                "source_type": "manual_test",
                "source_url": "https://test.example.com/financial"
            }
        ],
        "business_segments": [
            {
                "stock_code": STOCK_CODE,
                "report_date": REPORT_DATE,
                "segment_name": "Retail Banking",
                "segment_type": "business_segment",
                "revenue": 3000000000.00,
                "revenue_ratio": 0.60,
                "gross_margin": 0.45,
                "source_type": "manual_test",
                "source_url": "https://test.example.com/financial"
            },
            {
                "stock_code": STOCK_CODE,
                "report_date": REPORT_DATE,
                "segment_name": "Corporate Banking",
                "segment_type": "business_segment",
                "revenue": 2000000000.00,
                "revenue_ratio": 0.40,
                "gross_margin": 0.50,
                "source_type": "manual_test",
                "source_url": "https://test.example.com/financial"
            }
        ],
        "sync_vector_index": False
    }
}

staging_path = f"crawler/staging/financial/financial_{STOCK_CODE}_{REPORT_DATE}_{REPORT_TYPE}.json"
staging_text = json.dumps(staging, ensure_ascii=False, indent=2)
staging_bytes = staging_text.encode("utf-8")
staging_sha256 = hashlib.sha256(staging_bytes).hexdigest()

with open(staging_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(staging_text)

print(f"Staging written: {staging_path}")
print(f"Staging SHA256:  {staging_sha256}")

# ------------------------------------------------------------------
# 2. raw
# ------------------------------------------------------------------
raw = {
    "stock_code": STOCK_CODE,
    "report_date": REPORT_DATE,
    "report_type": REPORT_TYPE,
    "fiscal_year": FISCAL_YEAR,
    "raw_content": "Raw financial report PDF extracted text (mock)",
    "pages": 120,
    "source_url": "https://test.example.com/financial/pdf",
    "extracted_at": "2026-04-23T14:00:00+08:00"
}

raw_path = f"crawler/raw/financial/financial_{STOCK_CODE}_{REPORT_DATE}_{REPORT_TYPE}.json"
with open(raw_path, "w", encoding="utf-8") as f:
    json.dump(raw, f, ensure_ascii=False, indent=2)

print(f"Raw written:     {raw_path}")

# ------------------------------------------------------------------
# 3. quality report
# ------------------------------------------------------------------
quality_report = {
    "stock_code": STOCK_CODE,
    "report_date": REPORT_DATE,
    "report_type": REPORT_TYPE,
    "quality_score": 0.95,
    "checks": {
        "income_statement": {"passed": True, "missing_fields": []},
        "balance_sheet": {"passed": True, "missing_fields": []},
        "cashflow_statement": {"passed": True, "missing_fields": []},
        "financial_metrics": {"passed": True, "missing_fields": []},
        "financial_notes": {"passed": True, "missing_fields": []},
        "business_segments": {"passed": True, "missing_fields": []}
    },
    "warnings": [],
    "generated_at": "2026-04-23T14:00:00+08:00"
}

quality_path = f"crawler/staging/quality_reports/financial/financial_{STOCK_CODE}_{REPORT_DATE}_{REPORT_TYPE}_quality_report.json"
with open(quality_path, "w", encoding="utf-8") as f:
    json.dump(quality_report, f, ensure_ascii=False, indent=2)

print(f"Quality written: {quality_path}")

# ------------------------------------------------------------------
# 4. manifest
# ------------------------------------------------------------------
manifest = {
    "spec_version": "1.0",
    "job_id": f"financial_{STOCK_CODE}_{REPORT_DATE}_{REPORT_TYPE}",
    "created_at": "2026-04-23T14:00:00+08:00",
    "producer": {
        "system": "OpenClaw",
        "module": "financial_extractor",
        "run_id": "run_20260423_001"
    },
    "data_category": "financial_package",
    "time_window": {
        "begin_date": REPORT_DATE,
        "end_date": REPORT_DATE
    },
    "target": {
        "endpoint": "/api/ingest/financial-package",
        "ingest_package": "financial_package",
        "ingest_field": "financial_package",
        "target_table": "income_statement_hot,balance_sheet_hot,cashflow_statement_hot,financial_metric_hot,financial_notes_hot,business_segment_hot"
    },
    "files": {
        "raw_path": f"backend/crawler/raw/financial/financial_{STOCK_CODE}_{REPORT_DATE}_{REPORT_TYPE}.json",
        "staging_path": f"backend/crawler/staging/financial/financial_{STOCK_CODE}_{REPORT_DATE}_{REPORT_TYPE}.json",
        "quality_report_path": f"backend/crawler/staging/quality_reports/financial/financial_{STOCK_CODE}_{REPORT_DATE}_{REPORT_TYPE}_quality_report.json"
    },
    "record_stats": {
        "raw_count": 1,
        "staging_count": 9,
        "expected_write_count": 9
    },
    "checksum": {
        "staging_sha256": staging_sha256
    },
    "status": "ready"
}

manifest_path = f"ingest_center/manifests_financial/financial_{STOCK_CODE}_{REPORT_DATE}_{REPORT_TYPE}.json"
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print(f"Manifest written: {manifest_path}")
