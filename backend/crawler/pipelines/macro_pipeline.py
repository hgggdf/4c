from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from crawler.clients.stats_gov_client import build_macro_items, normalize_period


def _unwrap_series_results(series_payload: Iterable[dict] | dict | None) -> tuple[list[dict], str]:
    if isinstance(series_payload, dict):
        if isinstance(series_payload.get("series_results"), list):
            return [item for item in (series_payload.get("series_results") or []) if isinstance(item, dict)], str(series_payload.get("source") or "stats_gov").strip() or "stats_gov"
        nested = series_payload.get("data")
        if isinstance(nested, dict) and isinstance(nested.get("series_results"), list):
            return [item for item in (nested.get("series_results") or []) if isinstance(item, dict)], str(series_payload.get("source") or "stats_gov").strip() or "stats_gov"
        return [], str(series_payload.get("source") or "stats_gov").strip() or "stats_gov"
    return [item for item in (series_payload or []) if isinstance(item, dict)], "stats_gov"


def _looks_like_macro_item(raw: dict) -> bool:
    return all(key in raw for key in ("indicator_name", "period", "value"))


def build_macro_indicator_items(series_results: Iterable[dict] | dict | None) -> list[dict]:
    rows, source_type = _unwrap_series_results(series_results)
    items: list[dict] = []
    for series_result in rows:
        if _looks_like_macro_item(series_result):
            items.append(dict(series_result))
            continue
        items.extend(build_macro_items(series_result, source_type=source_type))
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
    items: list[dict] | dict,
    *,
    trace_id: str | None = None,
    operator_id: int | None = None,
) -> dict:
    normalized_items = build_macro_indicator_items(items)
    return {
        "trace_id": trace_id,
        "operator_id": operator_id,
        "items": filter_macro_items(normalized_items),
        "sync_vector_index": False,
    }


__all__ = [
    "build_macro_indicator_items",
    "build_macro_write_payload",
    "filter_macro_items",
]