from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from crawler.clients.stats_gov_client import DEFAULT_DBCODE, DEFAULT_INDICATOR_SPECS, StatsGovClient
from crawler.pipelines.macro_pipeline import build_macro_indicator_items, build_macro_write_payload
from crawler.scripts.common_ingest import count_written_items, post_json, response_message


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
def run_ingest(
    indicators: list[dict] | None = None,
    *,
    base_url: str,
    dbcode: str,
    limit_per_indicator: int,
    timeout: int,
    source_mode: str,
    strategy: str,
    dry_run: bool,
) -> dict:
    warnings: list[str] = []
    errors: list[str] = []

    requested_indicators = indicators or list(DEFAULT_INDICATOR_SPECS)
    if not indicators:
        warnings.append("using default macro indicators")
    result = StatsGovClient().fetch_series_bundle(
        requested_indicators,
        dbcode=dbcode,
        limit_per_indicator=max(limit_per_indicator, 1),
        source_mode=source_mode,
        strategy=strategy,
    )

    warnings.extend(result.get("warnings") or [])
    macro_items = build_macro_indicator_items(result)
    payload = build_macro_write_payload(result)
    fetched_count = len(payload.get("items") or [])
    written_count = 0

    if not result.get("success"):
        errors.append(str(result.get("error_message") or "macro fetch failed"))
    if str(result.get("source") or "").strip().lower() in {"local-sample", "input-file"}:
        errors.append("macro ingest rejected non-live source")
    if fetched_count <= 0:
        errors.append("macro payload is empty")

    if not errors and not dry_run:
        status_code, response_body = post_json(
            f"{base_url.rstrip('/')}/api/macro-write/macro-indicators",
            payload,
            timeout,
        )
        if status_code != 200 or not isinstance(response_body, dict) or not response_body.get("success", False):
            errors.append(f"macro ingest failed: HTTP {status_code} {response_message(response_body)}")
        else:
            written_count = count_written_items(response_body)

    kept_counts = Counter(item.get("indicator_name") for item in (payload.get("items") or []))
    raw_counts = Counter(item.get("indicator_name") for item in macro_items)
    indicator_details = [
        {
            "indicator_name": indicator_name,
            "fetched_count": raw_counts.get(indicator_name, 0),
            "written_count": kept_counts.get(indicator_name, 0) if not errors and not dry_run else 0,
        }
        for indicator_name in sorted(name for name in raw_counts if name)
    ]

    return {
        "success": not errors,
        "fetched_count": fetched_count,
        "written_count": written_count,
        "failed_count": 0 if not errors else 1,
        "source_mode": source_mode,
        "strategy_used": str(result.get("strategy") or strategy),
        "source": str(result.get("source") or "stats_gov"),
        "warnings": _merge_unique(warnings),
        "errors": _merge_unique(errors),
        "dry_run": dry_run,
        "dbcode": dbcode,
        "indicator_details": indicator_details,
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
    parser = argparse.ArgumentParser(description="Fetch macro indicator series and write them through the existing macro-write API.")
    parser.add_argument(
        "--indicator",
        action="append",
        dest="indicators",
        required=False,
        type=_parse_indicator_spec,
        help="Indicator spec in '指标名称|指标代码|单位(可选)' format. Repeatable.",
    )
    parser.add_argument("--dbcode", default=DEFAULT_DBCODE, help="stats.gov database code, for example hgyd or hgnd")
    parser.add_argument("--limit", type=int, default=12, help="Max periods to keep per indicator")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds")
    parser.add_argument("--source-mode", choices=["online", "auto"], default="online", help="Crawler source mode")
    parser.add_argument("--strategy", choices=["auto", "requests", "playwright"], default="auto", help="Crawler strategy")
    parser.add_argument("--dry-run", action="store_true", help="Build payload only and skip ingest POST requests")
    args = parser.parse_args()

    result = run_ingest(
        args.indicators,
        base_url=args.base_url,
        dbcode=args.dbcode,
        limit_per_indicator=max(args.limit, 1),
        timeout=args.timeout,
        source_mode=args.source_mode,
        strategy=args.strategy,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()