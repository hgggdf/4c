from __future__ import annotations

from typing import Any

import requests


def post_json(url: str, payload: dict, timeout: int) -> tuple[int, dict | str]:
    response = requests.post(url, json=payload, timeout=timeout)
    try:
        body: dict | str = response.json()
    except ValueError:
        body = response.text
    return response.status_code, body


def response_message(body: dict | str) -> str:
    if isinstance(body, dict):
        return str(body.get("message") or body.get("error_code") or body)
    return str(body)


def ensure_success_response(status_code: int, body: dict | str, *, operation: str) -> dict:
    if status_code != 200:
        raise RuntimeError(f"{operation} failed with HTTP {status_code}: {response_message(body)}")
    if not isinstance(body, dict) or not body.get("success", False):
        raise RuntimeError(f"{operation} failed: {response_message(body)}")
    return body


def count_payload_items(payload: dict, *section_names: str) -> int:
    names = section_names or tuple(key for key in payload if key != "sync_vector_index")
    total = 0
    for name in names:
        value = payload.get(name)
        if isinstance(value, list):
            total += len(value)
    return total


def count_written_items(body: dict | str) -> int:
    if not isinstance(body, dict):
        return 0
    data = body.get("data")
    return _count_totals(data)


def _count_totals(value: Any) -> int:
    if isinstance(value, dict):
        total = 0
        if isinstance(value.get("total"), int):
            total += int(value.get("total") or 0)
        for child_key, child_value in value.items():
            if child_key == "total":
                continue
            total += _count_totals(child_value)
        return total
    if isinstance(value, list):
        return sum(_count_totals(item) for item in value)
    return 0


def normalize_stock_code(value: str | None) -> str:
    digits = "".join(ch for ch in str(value or "").strip() if ch.isdigit())
    return digits[-6:] if len(digits) >= 6 else digits


def normalize_exchange(value: str | None) -> str | None:
    exchange = str(value or "").upper().strip()
    if exchange in {"SH", "SSE"}:
        return "SSE"
    if exchange in {"SZ", "SZSE"}:
        return "SZSE"
    if exchange in {"BJ", "BSE", "NEEQ"}:
        return "BSE"
    return exchange or None


def infer_exchange(stock_code: str, fallback: str | None = None) -> str | None:
    normalized_fallback = normalize_exchange(fallback)
    if normalized_fallback:
        return normalized_fallback
    code = normalize_stock_code(stock_code)
    if code.startswith(("60", "68", "90")):
        return "SSE"
    if code.startswith(("00", "20", "30")):
        return "SZSE"
    if code.startswith(("43", "83", "87", "92")):
        return "BSE"
    return None


def build_company_master_payload(
    stock_code: str,
    *,
    stock_name: str | None = None,
    full_name: str | None = None,
    exchange: str | None = None,
    aliases: list[str] | dict | None = None,
    source_type: str = "crawler",
    source_url: str | None = None,
) -> dict:
    normalized_stock_code = normalize_stock_code(stock_code)
    normalized_stock_name = str(stock_name or normalized_stock_code).strip() or normalized_stock_code
    payload = {
        "stock_code": normalized_stock_code,
        "stock_name": normalized_stock_name,
        "full_name": str(full_name or "").strip() or None,
        "exchange": infer_exchange(normalized_stock_code, exchange),
        "alias_json": aliases or None,
        "status": "active",
        "source_type": str(source_type or "crawler")[:32],
    }
    if source_url:
        payload["source_url"] = source_url
    return payload


def ensure_company_master(
    stock_code: str,
    *,
    base_url: str,
    timeout: int,
    stock_name: str | None = None,
    full_name: str | None = None,
    exchange: str | None = None,
    aliases: list[str] | dict | None = None,
    source_type: str = "crawler",
    source_url: str | None = None,
) -> dict:
    status_code, body = post_json(
        f"{base_url.rstrip('/')}/api/company-write/upsert-master",
        build_company_master_payload(
            stock_code,
            stock_name=stock_name,
            full_name=full_name,
            exchange=exchange,
            aliases=aliases,
            source_type=source_type,
            source_url=source_url,
        ),
        timeout,
    )
    return ensure_success_response(status_code, body, operation="company_master prewrite")
