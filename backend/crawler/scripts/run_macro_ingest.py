from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys

import requests


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from crawler.clients.stats_gov_client import StatsGovFetchError, fetch_indicator_series_live
from crawler.pipelines.macro_pipeline import (
    build_macro_indicator_items,
    build_macro_write_payload,
    filter_macro_items,
)


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


def _post_json(url: str, payload: dict, timeout: int) -> tuple[int, dict | str]:
    response = requests.post(url, json=payload, timeout=timeout)
    try:
        body: dict | str = response.json()
    except ValueError:
        body = response.text
    return response.status_code, body


def _load_series_results_from_file(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        series_results = raw
    elif isinstance(raw, dict):
        series_results = raw.get("series_results") or []
    else:
        raise ValueError("input JSON must be an array or an object containing 'series_results'")

    if not isinstance(series_results, list) or not series_results:
        raise ValueError("input JSON does not contain any series_results")
    return series_results


def run_ingest(
    indicators: list[dict] | None = None,
    *,
    base_url: str,
    dbcode: str,
    input_file: Path | None,
    limit_per_indicator: int,
    timeout: int,
) -> dict:
    indicators = indicators or []
    series_results: list[dict] = []
    fetched_counts: dict[str, int] = {}
    mode = "input-file" if input_file is not None else "live"

    if input_file is not None:
        series_results = _load_series_results_from_file(input_file)
        for series_result in series_results:
            indicator_name = str(series_result.get("indicator_name") or series_result.get("indicator_code") or "").strip()
            raw_count = len(((series_result.get("response") or {}).get("returndata") or {}).get("datanodes") or [])
            if indicator_name:
                fetched_counts[indicator_name] = raw_count
    else:
        for indicator in indicators:
            try:
                series_result = fetch_indicator_series_live(
                    indicator["indicator_code"],
                    indicator_name=indicator["indicator_name"],
                    unit=indicator.get("unit"),
                    dbcode=dbcode,
                    timeout=timeout,
                    pagesize=max(limit_per_indicator, 12),
                )
            except StatsGovFetchError as exc:
                raise RuntimeError(
                    "live fetch from stats.gov.cn failed. "
                    "You can retry with a browser-capable environment or use '--input-file crawler/samples/macro_sample.json'. "
                    f"details: {exc}"
                ) from exc

            raw_count = len(((series_result.get("response") or {}).get("returndata") or {}).get("datanodes") or [])
            fetched_counts[indicator["indicator_name"]] = raw_count
            series_results.append(series_result)

    built_items = build_macro_indicator_items(series_results)
    filtered_items = filter_macro_items(built_items, limit_per_indicator=limit_per_indicator)
    if not filtered_items:
        raise RuntimeError("no macro items were built from the provided macro data")

    payload = build_macro_write_payload(filtered_items)
    status_code, response_body = _post_json(
        f"{base_url.rstrip('/')}/api/macro-write/macro-indicators",
        payload,
        timeout,
    )
    kept_counts = Counter(item["indicator_name"] for item in filtered_items)

    return {
        "mode": mode,
        "input_file": str(input_file) if input_file is not None else None,
        "dbcode": dbcode,
        "indicator_count": len(indicators) if indicators else len(series_results),
        "item_count": len(filtered_items),
        "indicators": [
            {
                "indicator_name": indicator_name,
                "indicator_code": indicator_code,
                "unit": unit,
                "fetched_count": fetched_counts.get(indicator_name, 0),
                "write_count": kept_counts.get(indicator_name, 0),
            }
            for indicator_name, indicator_code, unit in [
                (
                    str(series_result.get("indicator_name") or series_result.get("indicator_code") or "").strip(),
                    str(series_result.get("indicator_code") or "").strip() or None,
                    series_result.get("unit"),
                )
                for series_result in series_results
            ]
            if indicator_name
        ],
        "status_code": status_code,
        "response": response_body,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch macro indicator series from stats.gov.cn and write them through the existing macro-write API."
    )
    parser.add_argument(
        "--indicator",
        action="append",
        dest="indicators",
        required=False,
        type=_parse_indicator_spec,
        help="Indicator spec in '指标名称|指标代码|单位(可选)' format. Example: '居民消费价格指数(上年同月=100)|A01010101|%%'.",
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        help="Read macro series results from a local JSON file instead of fetching live from stats.gov.cn.",
    )
    parser.add_argument("--dbcode", default="hgyd", help="stats.gov database code, for example hgyd or hgnd")
    parser.add_argument("--limit", type=int, default=12, help="Max periods to keep per indicator")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds")
    args = parser.parse_args()

    if args.input_file is None and not args.indicators:
        parser.error("either --indicator or --input-file is required")
    if args.input_file is not None and not args.input_file.exists():
        parser.error(f"input file does not exist: {args.input_file}")

    try:
        result = run_ingest(
            args.indicators,
            base_url=args.base_url,
            dbcode=args.dbcode,
            input_file=args.input_file,
            limit_per_indicator=max(args.limit, 1),
            timeout=args.timeout,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()