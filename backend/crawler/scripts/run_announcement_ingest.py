from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from crawler.clients.exchange_client import ExchangeAnnouncementClient
from crawler.pipelines.announcement_pipeline import build_announcement_package_payload
from crawler.reference.pharma_company_registry import get_company
from crawler.scripts.common_ingest import (
    count_payload_items,
    count_written_items,
    ensure_company_master,
    infer_exchange,
    normalize_stock_code,
    post_json,
    response_message,
)


ANNOUNCEMENT_SECTIONS = (
    "raw_announcements",
    "structured_announcements",
    "drug_approvals",
    "clinical_trials",
    "procurement_events",
    "regulatory_risks",
)


def run_ingest(
    stock_code: str,
    *,
    base_url: str,
    sync_vector_index: bool,
    timeout: int,
    source_mode: str,
    strategy: str,
    limit: int,
    begin_date: str | None,
    end_date: str | None,
    announcement_type: str,
    dry_run: bool,
) -> dict:
    normalized_stock_code = normalize_stock_code(stock_code)
    company = get_company(normalized_stock_code) or {}
    result = ExchangeAnnouncementClient().fetch_announcements(
        normalized_stock_code,
        begin_date=begin_date,
        end_date=end_date,
        announcement_type=announcement_type,
        limit=max(limit, 1),
        source_mode=source_mode,
        strategy=strategy,
    )
    warnings = list(result.get("warnings") or [])
    errors: list[str] = []

    payload = build_announcement_package_payload(result, normalized_stock_code, sync_vector_index=sync_vector_index)
    section_counts = {
        section: len(payload.get(section) or [])
        for section in ANNOUNCEMENT_SECTIONS
    }
    fetched_count = count_payload_items(payload, *ANNOUNCEMENT_SECTIONS)
    written_count = 0
    master_written = False

    raw_items = payload.get("raw_announcements") or []
    exchange = infer_exchange(normalized_stock_code, (raw_items[0].get("exchange") if raw_items else company.get("exchange")))
    stock_name = str(company.get("name") or normalized_stock_code).strip() or normalized_stock_code
    aliases = company.get("aliases") or None

    if not result.get("success"):
        errors.append(str(result.get("error_message") or "announcement fetch failed"))
    if str(result.get("source") or "").strip().lower() in {"local-sample", "input-file"}:
        errors.append("announcement ingest rejected non-live source")
    if fetched_count <= 0:
        errors.append("announcement payload is empty")

    if not errors and not dry_run:
        try:
            ensure_company_master(
                normalized_stock_code,
                base_url=base_url,
                timeout=timeout,
                stock_name=stock_name,
                exchange=exchange,
                aliases=aliases,
                source_type=f"announcement_{result.get('source') or 'crawler'}",
            )
            master_written = True
        except Exception as exc:
            errors.append(str(exc))

    if not errors and not dry_run:
        status_code, response_body = post_json(
            f"{base_url.rstrip('/')}/api/ingest/announcement-package",
            payload,
            timeout,
        )
        if status_code != 200 or not isinstance(response_body, dict) or not response_body.get("success", False):
            errors.append(f"announcement ingest failed: HTTP {status_code} {response_message(response_body)}")
        else:
            written_count = count_written_items(response_body)

    return {
        "stock_code": normalized_stock_code,
        "success": not errors,
        "fetched_count": fetched_count,
        "written_count": written_count,
        "failed_count": 0 if not errors else 1,
        "source_mode": source_mode,
        "strategy_used": str(result.get("strategy") or strategy),
        "source": str(result.get("source") or "exchange"),
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
    parser = argparse.ArgumentParser(description="Fetch announcements and ingest them through the existing announcement package API.")
    parser.add_argument("stock_codes", nargs="+", help="One or more stock codes, for example 600276")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds")
    parser.add_argument("--source-mode", choices=["online", "auto"], default="online", help="Crawler source mode")
    parser.add_argument("--strategy", choices=["auto", "requests", "playwright"], default="auto", help="Crawler strategy")
    parser.add_argument("--limit", type=int, default=20, help="Max number of announcements to fetch per stock")
    parser.add_argument("--begin-date", help="Announcement begin date, for example 2026-01-01")
    parser.add_argument("--end-date", help="Announcement end date, for example 2026-12-31")
    parser.add_argument("--announcement-type", default="全部", help="Announcement category filter")
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
            limit=args.limit,
            begin_date=args.begin_date,
            end_date=args.end_date,
            announcement_type=args.announcement_type,
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