from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from crawler.clients.stats_gov_client import build_macro_items, normalize_period


def build_macro_indicator_items(series_results: Iterable[dict]) -> list[dict]:
    items: list[dict] = []
    for series_result in series_results:
        items.extend(build_macro_items(series_result))
    return items


def filter_macro_items(
    items: list[dict],
    *,
    indicator_names: list[str] | None = None,
    periods: list[str] | None = None,
    limit_per_indicator: int | None = None,
) -> list[dict]:
    allowed_indicator_names = {str(name).strip() for name in indicator_names or [] if str(name).strip()}
    allowed_periods = {
        normalized
        for normalized in (normalize_period(period) for period in (periods or []))
        if normalized
    }

    deduped: dict[tuple[str, str], dict] = {}
    for raw in items:
        indicator_name = str(raw.get("indicator_name") or "").strip()
        period = normalize_period(raw.get("period"))
        value = raw.get("value")

        if not indicator_name or not period or value in (None, "", "--"):
            continue
        if allowed_indicator_names and indicator_name not in allowed_indicator_names:
            continue
        if allowed_periods and period not in allowed_periods:
            continue

        deduped[(indicator_name, period)] = {
            "indicator_name": indicator_name,
            "period": period,
            "value": str(value),
            "unit": str(raw.get("unit") or "").strip() or None,
            "source_type": str(raw.get("source_type") or "stats_gov").strip() or "stats_gov",
            "source_url": str(raw.get("source_url") or "").strip() or None,
        }

    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in deduped.values():
        grouped[item["indicator_name"]].append(item)

    filtered: list[dict] = []
    for indicator_name in sorted(grouped):
        series = sorted(grouped[indicator_name], key=lambda item: item["period"], reverse=True)
        if limit_per_indicator is not None and limit_per_indicator > 0:
            series = series[:limit_per_indicator]
        filtered.extend(series)
    return filtered


def build_macro_write_payload(
    items: list[dict],
    *,
    trace_id: str | None = None,
    operator_id: int | None = None,
) -> dict:
    return {
        "trace_id": trace_id,
        "operator_id": operator_id,
        "items": filter_macro_items(items),
        "sync_vector_index": False,
    }


__all__ = [
    "build_macro_indicator_items",
    "build_macro_write_payload",
    "filter_macro_items",
]