from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from crawler.clients.akshare_client import AkshareCrawlerClient
from crawler.clients.eastmoney_client import EastmoneyClient
from crawler.clients.exchange_client import ExchangeAnnouncementClient
from crawler.clients.stats_gov_client import DEFAULT_INDICATOR_SPECS, StatsGovClient


def _summarize_result(name: str, result: dict, *, item_count: int | None = None, extra: dict | None = None) -> dict:
    summary = {
        "name": name,
        "success": bool(result.get("success")),
        "source": str(result.get("source") or ""),
        "strategy_used": str(result.get("strategy") or ""),
        "warnings": list(result.get("warnings") or []),
        "error": str(result.get("error_message") or "") or None,
    }
    if item_count is None:
        summary["item_count"] = len(result.get("items") or [])
    else:
        summary["item_count"] = item_count
    if extra:
        summary.update(extra)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Check crawler source availability without writing data into the backend.")
    parser.add_argument("stock_codes", nargs="*", default=["600276"], help="Stock codes used for stock-specific source checks")
    parser.add_argument("--keyword", default="医药", help="Keyword used for industry research report checks")
    parser.add_argument("--source-mode", choices=["online", "fallback", "auto"], default="auto", help="Crawler source mode")
    parser.add_argument("--strategy", choices=["auto", "requests", "playwright", "fallback"], default="auto", help="Crawler strategy")
    parser.add_argument("--limit", type=int, default=3, help="Max number of items to probe per source")
    args = parser.parse_args()

    stock_code = args.stock_codes[0]
    eastmoney = EastmoneyClient()
    exchange = ExchangeAnnouncementClient()
    financial = AkshareCrawlerClient()
    macro = StatsGovClient()

    financial_result = financial.fetch_financial_bundle(stock_code, source_mode=args.source_mode, strategy="fallback" if args.strategy == "fallback" else "auto")
    financial_bundle = financial_result.get("data") or {}
    financial_sections = sum(
        len(financial_bundle.get(section) or [])
        for section in (
            "financial_abstract",
            "financial_indicators",
            "income_statements_raw",
            "balance_sheets_raw",
            "cashflow_statements_raw",
        )
    )

    announcement_result = exchange.fetch_announcements(
        stock_code,
        limit=max(args.limit, 1),
        source_mode=args.source_mode,
        strategy=args.strategy,
    )
    industry_report_result = eastmoney.fetch_industry_reports(
        keyword=args.keyword,
        limit=max(args.limit, 1),
        source_mode=args.source_mode,
        strategy=args.strategy,
    )
    stock_report_result = eastmoney.fetch_stock_reports(
        stock_code,
        limit=max(args.limit, 1),
        source_mode=args.source_mode,
        strategy=args.strategy,
    )
    macro_result = macro.fetch_series_bundle(
        list(DEFAULT_INDICATOR_SPECS),
        limit_per_indicator=max(args.limit, 1),
        source_mode=args.source_mode,
        strategy=args.strategy,
    )
    macro_series = ((macro_result.get("data") or {}).get("series_results") or [])

    summary = {
        "source_mode": args.source_mode,
        "strategy": args.strategy,
        "checks": [
            _summarize_result("financial", financial_result, item_count=financial_sections, extra={"stock_code": stock_code}),
            _summarize_result("announcement", announcement_result, extra={"stock_code": stock_code}),
            _summarize_result("research_industry", industry_report_result, extra={"keyword": args.keyword}),
            _summarize_result("research_stock", stock_report_result, extra={"stock_code": stock_code}),
            _summarize_result("macro", macro_result, item_count=len(macro_series), extra={"indicator_count": len(macro_series)}),
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()