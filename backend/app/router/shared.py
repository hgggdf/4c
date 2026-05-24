"""Backward-compatible entrypoint for shared service helpers."""

from app.service.shared import (
    build_quote_payload,
    ensure_demo_user,
    extract_stock_code,
    get_latest_trade_rows,
    normalize_percent,
    resolve_company,
    serialize_kline_row,
    to_float,
)

__all__ = [
    "build_quote_payload",
    "ensure_demo_user",
    "extract_stock_code",
    "get_latest_trade_rows",
    "normalize_percent",
    "resolve_company",
    "serialize_kline_row",
    "to_float",
]
