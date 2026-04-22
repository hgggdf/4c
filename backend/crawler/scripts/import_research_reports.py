from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from crawler.scripts.run_research_report_ingest import run_ingest


def _parse_stock_target(value: str) -> str:
    parts = [part.strip() for part in value.split("|", 1)]
    if len(parts) != 2 or not parts[0]:
        raise argparse.ArgumentTypeError("stock must use '股票代码|股票名称' format")
    return parts[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Compatibility wrapper for research report ingestion through the formal news package API.")
    parser.add_argument("stock_codes", nargs="*", help="Optional stock codes for stock research reports, for example 600276")
    parser.add_argument("--stock", action="append", dest="stocks", type=_parse_stock_target, help="Legacy stock target in '股票代码|股票名称' format. Repeatable.")
    parser.add_argument("--industry-keyword", default="医药", dest="keyword", help="Keyword used to fetch industry reports")
    parser.add_argument("--industry-limit", type=int, default=6, help="Max number of industry reports to fetch")
    parser.add_argument("--stock-limit", type=int, default=3, help="Max number of reports to fetch per stock")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds")
    parser.add_argument("--source-mode", choices=["online", "fallback", "auto"], default="auto", help="Crawler source mode")
    parser.add_argument("--strategy", choices=["auto", "requests", "playwright", "fallback"], default="auto", help="Crawler strategy")
    parser.add_argument("--dry-run", action="store_true", help="Build payload only and skip ingest POST requests")
    parser.add_argument("--skip-background", action="store_true", help="Deprecated and ignored; background knowledge is no longer imported")
    parser.add_argument("--no-sync-vector-index", action="store_false", dest="sync_vector_index", help="Disable vector sync")
    parser.set_defaults(sync_vector_index=True)
    args = parser.parse_args()

    stock_codes = list(args.stock_codes) + list(args.stocks or [])
    result = run_ingest(
        stock_codes,
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
    if args.skip_background:
        result["warnings"] = list(result.get("warnings") or []) + ["--skip-background is ignored in the new formal ingest flow"]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()