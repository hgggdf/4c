from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from crawler.scripts.run_announcement_ingest import run_ingest as run_announcement_ingest
from crawler.scripts.run_financial_ingest import run_ingest as run_financial_ingest
from crawler.scripts.run_macro_ingest import run_ingest as run_macro_ingest
from crawler.scripts.run_research_report_ingest import run_ingest as run_research_report_ingest


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


def _as_list(value: str | list[str] | None) -> list[str]:
    if isinstance(value, list):
        return [str(item or "") for item in value]
    if value is None:
        return []
    return [str(value)]


def _parse_indicator_spec(value: str) -> dict:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) not in {2, 3}:
        raise argparse.ArgumentTypeError("indicator must use '指标名称|指标代码|单位(可选)' format")
    indicator_name, indicator_code = parts[0], parts[1]
    unit = parts[2] if len(parts) == 3 else None
    if not indicator_name or not indicator_code:
        raise argparse.ArgumentTypeError("indicator name and code are required")
    return {
        "indicator_name": indicator_name,
        "indicator_code": indicator_code,
        "unit": unit or None,
    }


def _summarize_target_results(results: list[dict]) -> dict:
    return {
        "success": all(item.get("success") for item in results),
        "fetched_count": sum(int(item.get("fetched_count") or 0) for item in results),
        "written_count": sum(int(item.get("written_count") or 0) for item in results),
        "failed_count": sum(int(item.get("failed_count") or 0) for item in results),
        "strategy_used": _merge_unique([str(item.get("strategy_used") or "") for item in results]),
        "warnings": _merge_unique([warning for item in results for warning in (item.get("warnings") or [])]),
        "errors": _merge_unique([error for item in results for error in (item.get("errors") or [])]),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all crawler ingest chains and aggregate their summaries.")
    parser.add_argument("stock_codes", nargs="+", help="One or more stock codes, for example 600276")
    parser.add_argument("--keyword", default="医药", help="Industry keyword used for research report fetching")
    parser.add_argument("--macro-indicator", action="append", dest="macro_indicators", type=_parse_indicator_spec, help="Optional macro indicator spec in '指标名称|指标代码|单位(可选)' format")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds")
    parser.add_argument("--source-mode", choices=["online", "fallback", "auto"], default="auto", help="Crawler source mode")
    parser.add_argument("--strategy", choices=["auto", "requests", "playwright", "fallback"], default="auto", help="Crawler strategy")
    parser.add_argument("--dry-run", action="store_true", help="Build payloads only and skip write API POST requests")
    parser.add_argument("--no-sync-vector-index", action="store_false", dest="sync_vector_index", help="Disable vector sync")
    parser.add_argument("--skip-financial", action="store_true", help="Skip the financial ingest chain")
    parser.add_argument("--skip-announcement", action="store_true", help="Skip the announcement ingest chain")
    parser.add_argument("--skip-macro", action="store_true", help="Skip the macro ingest chain")
    parser.add_argument("--skip-research", action="store_true", help="Skip the research report ingest chain")
    parser.set_defaults(sync_vector_index=True)
    args = parser.parse_args()

    sections: dict[str, dict] = {}

    if not args.skip_financial:
        sections["financial"] = _summarize_target_results(
            [
                run_financial_ingest(
                    stock_code,
                    base_url=args.base_url,
                    sync_vector_index=args.sync_vector_index,
                    timeout=args.timeout,
                    source_mode=args.source_mode,
                    strategy=args.strategy,
                    history_days=120,
                    dry_run=args.dry_run,
                )
                for stock_code in args.stock_codes
            ]
        )

    if not args.skip_announcement:
        sections["announcement"] = _summarize_target_results(
            [
                run_announcement_ingest(
                    stock_code,
                    base_url=args.base_url,
                    sync_vector_index=args.sync_vector_index,
                    timeout=args.timeout,
                    source_mode=args.source_mode,
                    strategy=args.strategy,
                    limit=20,
                    begin_date=None,
                    end_date=None,
                    announcement_type="全部",
                    dry_run=args.dry_run,
                )
                for stock_code in args.stock_codes
            ]
        )

    if not args.skip_macro:
        sections["macro"] = run_macro_ingest(
            args.macro_indicators,
            base_url=args.base_url,
            dbcode="hgyd",
            input_file=None,
            limit_per_indicator=12,
            timeout=args.timeout,
            source_mode=args.source_mode,
            strategy=args.strategy,
            dry_run=args.dry_run,
        )

    if not args.skip_research:
        sections["research_report"] = run_research_report_ingest(
            args.stock_codes,
            keyword=args.keyword,
            stock_limit=3,
            industry_limit=6,
            base_url=args.base_url,
            timeout=args.timeout,
            source_mode=args.source_mode,
            strategy=args.strategy,
            sync_vector_index=args.sync_vector_index,
            dry_run=args.dry_run,
        )

    summary = {
        "success": all(section.get("success") for section in sections.values()),
        "fetched_count": sum(int(section.get("fetched_count") or 0) for section in sections.values()),
        "written_count": sum(int(section.get("written_count") or 0) for section in sections.values()),
        "failed_count": sum(int(section.get("failed_count") or 0) for section in sections.values()),
        "source_mode": args.source_mode,
        "strategy_used": _merge_unique([strategy for section in sections.values() for strategy in _as_list(section.get("strategy_used"))]) if sections else [],
        "warnings": _merge_unique([warning for section in sections.values() for warning in (section.get("warnings") or [])]),
        "errors": _merge_unique([error for section in sections.values() for error in (section.get("errors") or [])]),
        "sections": sections,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()