from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from crawler.clients.akshare_client import AkshareCrawlerClient
from crawler.pipelines.financial_pipeline import build_financial_package_payload
from crawler.scripts.common_ingest import (
    count_payload_items,
    count_written_items,
    ensure_company_master,
    infer_exchange,
    normalize_stock_code,
    post_json,
    response_message,
)


FINANCIAL_SECTIONS = (
    "income_statements",
    "balance_sheets",
    "cashflow_statements",
    "financial_metrics",
    "financial_notes",
    "business_segments",
    "stock_daily",
)


def _map_strategy(strategy: str) -> tuple[str, list[str]]:
    normalized = str(strategy or "auto").strip().lower() or "auto"
    if normalized in {"requests", "playwright"}:
        return "auto", [f"financial source ignores '{normalized}' and uses akshare sdk path"]
    return "auto", []


def run_ingest(
    stock_code: str,
    *,
    base_url: str,
    sync_vector_index: bool,
    timeout: int,
    source_mode: str,
    strategy: str,
    history_days: int,
    dry_run: bool,
) -> dict:
    normalized_stock_code = normalize_stock_code(stock_code)
    client_strategy, strategy_warnings = _map_strategy(strategy)
    result = AkshareCrawlerClient().fetch_financial_bundle(
        normalized_stock_code,
        history_days=max(history_days, 1),
        source_mode=source_mode,
        strategy=client_strategy,
    )
    warnings = strategy_warnings + list(result.get("warnings") or [])
    errors: list[str] = []

    payload = build_financial_package_payload(result, normalized_stock_code, sync_vector_index=sync_vector_index)
    section_counts = {
        section: len(payload.get(section) or [])
        for section in FINANCIAL_SECTIONS
    }
    fetched_count = count_payload_items(payload, *FINANCIAL_SECTIONS)
    written_count = 0
    master_written = False

    bundle = result.get("data") or {}
    company_info = bundle.get("company_info") or {}
    stock_name = str(bundle.get("name") or normalized_stock_code).strip() or normalized_stock_code
    full_name = str(company_info.get("股票名称") or company_info.get("公司名称") or "").strip() or None
    exchange = infer_exchange(normalized_stock_code, bundle.get("exchange"))
    aliases = bundle.get("aliases") or None

    if not result.get("success"):
        errors.append(str(result.get("error_message") or "financial fetch failed"))
    if str(result.get("source") or "").strip().lower() in {"local-sample", "input-file"}:
        errors.append("financial ingest rejected non-live source")
    if fetched_count <= 0:
        errors.append("financial payload is empty")

    if not errors and not dry_run:
        try:
            ensure_company_master(
                normalized_stock_code,
                base_url=base_url,
                timeout=timeout,
                stock_name=stock_name,
                full_name=full_name,
                exchange=exchange,
                aliases=aliases,
                source_type=f"financial_{result.get('source') or 'crawler'}",
            )
            master_written = True
        except Exception as exc:
            errors.append(str(exc))

    if not errors and not dry_run:
        status_code, response_body = post_json(
            f"{base_url.rstrip('/')}/api/ingest/financial-package",
            payload,
            timeout,
        )
        if status_code != 200 or not isinstance(response_body, dict) or not response_body.get("success", False):
            errors.append(f"financial ingest failed: HTTP {status_code} {response_message(response_body)}")
        else:
            written_count = count_written_items(response_body)

    return {
        "stock_code": normalized_stock_code,
        "success": not errors,
        "fetched_count": fetched_count,
        "written_count": written_count,
        "failed_count": 0 if not errors else 1,
        "source_mode": source_mode,
        "strategy_used": str(result.get("strategy") or client_strategy),
        "source": str(result.get("source") or "akshare"),
        "warnings": warnings,
        "errors": errors,
        "dry_run": dry_run,
        "company_master_written": master_written,
        "section_counts": section_counts,
    }


def _merge_unique(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch financial data and ingest it through the existing financial package API.")
    parser.add_argument("stock_codes", nargs="+", help="One or more stock codes, for example 600276")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds")
    parser.add_argument("--source-mode", choices=["online", "auto"], default="online", help="Crawler source mode")
    parser.add_argument("--strategy", choices=["auto", "requests", "playwright"], default="auto", help="Crawler strategy")
    parser.add_argument("--history-days", type=int, default=120, help="Historical daily price window used for stock_daily")
    parser.add_argument("--dry-run", action="store_true", help="Build payload only and skip company master / ingest POST requests")
    parser.add_argument("--no-sync-vector-index", action="store_false", dest="sync_vector_index", help="Disable vector sync")
    parser.set_defaults(sync_vector_index=True)
    args = parser.parse_args()

    results = [
        run_ingest(
            stock_code,
            base_url=args.base_url,
            sync_vector_index=args.sync_vector_index,
            timeout=args.timeout,
            source_mode=args.source_mode,
            strategy=args.strategy,
            history_days=args.history_days,
            dry_run=args.dry_run,
        )
        for stock_code in args.stock_codes
    ]

    summary = {
        "success": all(item.get("success") for item in results),
        "fetched_count": sum(int(item.get("fetched_count") or 0) for item in results),
        "written_count": sum(int(item.get("written_count") or 0) for item in results),
        "failed_count": sum(int(item.get("failed_count") or 0) for item in results),
        "source_mode": args.source_mode,
        "strategy_used": _merge_unique([str(item.get("strategy_used") or "") for item in results]),
        "warnings": _merge_unique([warning for item in results for warning in (item.get("warnings") or [])]),
        "errors": _merge_unique([error for item in results for error in (item.get("errors") or [])]),
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()