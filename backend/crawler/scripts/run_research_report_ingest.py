from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from crawler.clients.eastmoney_client import EastmoneyClient
from crawler.pipelines.research_report_pipeline import build_research_report_news_package_payload
from crawler.scripts.common_ingest import count_written_items, post_json, response_message


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


def _collect_report_result(scope: str, target: str, result: dict) -> dict:
    items = result.get("items") or []
    return {
        "scope": scope,
        "target": target,
        "success": bool(result.get("success")),
        "fetched_count": len(items),
        "strategy_used": str(result.get("strategy") or "auto"),
        "source": str(result.get("source") or "eastmoney"),
        "warnings": list(result.get("warnings") or []),
        "errors": [str(result.get("error_message"))] if result.get("error_message") else [],
        "items": items,
    }


def run_ingest(
    stock_codes: list[str],
    *,
    keyword: str,
    stock_limit: int,
    industry_limit: int,
    base_url: str,
    timeout: int,
    source_mode: str,
    strategy: str,
    sync_vector_index: bool,
    dry_run: bool,
) -> dict:
    client = EastmoneyClient()
    fetch_results: list[dict] = []

    if industry_limit > 0:
        fetch_results.append(
            _collect_report_result(
                "industry",
                keyword,
                client.fetch_industry_reports(
                    keyword=keyword,
                    limit=max(industry_limit, 1),
                    source_mode=source_mode,
                    strategy=strategy,
                ),
            )
        )

    for stock_code in stock_codes:
        fetch_results.append(
            _collect_report_result(
                "stock",
                stock_code,
                client.fetch_stock_reports(
                    stock_code,
                    limit=max(stock_limit, 1),
                    source_mode=source_mode,
                    strategy=strategy,
                ),
            )
        )

    combined_items = [item for result in fetch_results for item in result.get("items") or []]
    payload = build_research_report_news_package_payload({"items": combined_items}, sync_vector_index=sync_vector_index)
    fetched_count = len(payload.get("news_raw") or [])
    warnings = _merge_unique([warning for result in fetch_results for warning in (result.get("warnings") or [])])
    errors = _merge_unique([error for result in fetch_results for error in (result.get("errors") or [])])
    written_count = 0

    if fetched_count <= 0:
        errors = _merge_unique(errors + ["research report payload is empty"])
    for result in fetch_results:
        source_name = str(result.get("source") or "").strip().lower()
        if source_name in {"local-sample", "input-file"}:
            errors = _merge_unique(errors + [f"research report ingest rejected non-live source for {result.get('scope')}"])

    if not errors and not dry_run:
        status_code, response_body = post_json(
            f"{base_url.rstrip('/')}/api/ingest/news-package",
            payload,
            timeout,
        )
        if status_code != 200 or not isinstance(response_body, dict) or not response_body.get("success", False):
            errors = _merge_unique(errors + [f"research report ingest failed: HTTP {status_code} {response_message(response_body)}"])
        else:
            written_count = count_written_items(response_body)

    sanitized_results = []
    for result in fetch_results:
        sanitized = dict(result)
        sanitized.pop("items", None)
        sanitized["failed_count"] = 0 if sanitized.get("success") else 1
        sanitized_results.append(sanitized)

    return {
        "success": not errors,
        "fetched_count": fetched_count,
        "written_count": written_count,
        "failed_count": sum(int(item.get("failed_count") or 0) for item in sanitized_results) + (1 if errors and dry_run is False and written_count == 0 and fetched_count > 0 else 0),
        "source_mode": source_mode,
        "strategy_used": _merge_unique([str(item.get("strategy_used") or "") for item in sanitized_results]),
        "warnings": warnings,
        "errors": errors,
        "dry_run": dry_run,
        "results": sanitized_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch research reports and ingest them through the existing news package API.")
    parser.add_argument("stock_codes", nargs="*", help="Optional stock codes for stock research reports, for example 600276")
    parser.add_argument("--keyword", "--industry-keyword", default="医药", dest="keyword", help="Keyword used to fetch industry research reports")
    parser.add_argument("--stock-limit", type=int, default=3, help="Max number of reports to fetch per stock")
    parser.add_argument("--industry-limit", type=int, default=6, help="Max number of industry reports to fetch")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds")
    parser.add_argument("--source-mode", choices=["online", "auto"], default="online", help="Crawler source mode")
    parser.add_argument("--strategy", choices=["auto", "requests", "playwright"], default="auto", help="Crawler strategy")
    parser.add_argument("--dry-run", action="store_true", help="Build payload only and skip ingest POST requests")
    parser.add_argument("--no-sync-vector-index", action="store_false", dest="sync_vector_index", help="Disable vector sync")
    parser.set_defaults(sync_vector_index=True)
    args = parser.parse_args()

    result = run_ingest(
        args.stock_codes,
        keyword=args.keyword,
        stock_limit=max(args.stock_limit, 1),
        industry_limit=max(args.industry_limit, 0),
        base_url=args.base_url,
        timeout=args.timeout,
        source_mode=args.source_mode,
        strategy=args.strategy,
        sync_vector_index=args.sync_vector_index,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()