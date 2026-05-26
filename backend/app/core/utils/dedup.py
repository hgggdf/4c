from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_SPACE_RE = re.compile(r"\s+")
_TITLE_PREFIX_RE = re.compile(r"^(?:[a-z]{0,3}\d{6}|\d{6})\s*[:：\-_\s]+", re.IGNORECASE)

_IGNORED_CONTENT_FIELDS = {
    "id",
    "dedup_key",
    "content_hash",
    "query_count",
    "created_at",
    "updated_at",
    "vector_status",
    "announcement_uid",
    "report_uid",
    "news_uid",
    "file_path",
    "file_type",
    "original_filename",
}


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text)
    return _SPACE_RE.sub(" ", text).strip()


def normalize_title(value: Any) -> str:
    title = normalize_text(value)
    title = _TITLE_PREFIX_RE.sub("", title)
    return title.casefold()


def normalize_key_part(value: Any) -> str:
    return normalize_text(value).casefold()


def normalize_date_part(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    return normalize_text(value)


def normalize_url(value: Any) -> str:
    raw = normalize_text(value)
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return raw.casefold()

    query_items = sorted(
        [
            (key, val)
            for key, val in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
        ]
    )
    query = urlencode(query_items, doseq=True)
    return urlunsplit(
        (
            parsed.scheme.casefold(),
            parsed.netloc.casefold(),
            parsed.path.rstrip("/"),
            query,
            "",
        )
    )


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_parts(data_type: str, parts: list[Any]) -> str:
    canonical = "\x1f".join(normalize_key_part(part) for part in parts)
    return f"{data_type}:{_hash_text(canonical)}"


def build_dedup_key(data_type: str, item: dict[str, Any]) -> str:
    if data_type == "financial":
        return _hash_parts(
            data_type,
            [
                item.get("stock_code"),
                item.get("report_type") or "annual",
                normalize_date_part(item.get("report_date") or item.get("trade_date")),
            ],
        )

    if data_type == "announcement":
        return _hash_parts(
            data_type,
            [
                item.get("stock_code"),
                normalize_date_part(item.get("publish_date")),
                normalize_title(item.get("title")),
            ],
        )

    if data_type == "research_report":
        scope_type = item.get("scope_type") or "company"
        scope_key = item.get("stock_code") or item.get("industry_code") or ""
        return _hash_parts(
            data_type,
            [
                scope_type,
                scope_key,
                normalize_date_part(item.get("publish_date")),
                item.get("report_org"),
                normalize_title(item.get("title")),
            ],
        )

    if data_type == "news":
        source_url = normalize_url(item.get("source_url"))
        if source_url:
            return _hash_parts(data_type, ["url", source_url])
        return _hash_parts(
            data_type,
            [
                item.get("source_name"),
                normalize_date_part(item.get("publish_time")),
                normalize_title(item.get("title")),
            ],
        )

    if data_type == "pipeline_drug":
        # 不把 trial_phase 放进去：阶段会推进，dedup_key 必须保持稳定。
        canonical = item.get("canonical_drug_name") or item.get("drug_name") or ""
        return _hash_parts(
            data_type,
            [
                item.get("stock_code"),
                normalize_key_part(canonical),
                normalize_key_part(item.get("indication_norm") or item.get("indication") or ""),
            ],
        )

    raise ValueError(f"Unsupported dedup data_type: {data_type}")


def _normalize_content_value(value: Any) -> Any:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value.normalize())
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, dict):
        return {str(k): _normalize_content_value(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_normalize_content_value(v) for v in value]
    return normalize_text(value)


def build_content_hash(data_type: str, item: dict[str, Any]) -> str:
    payload = {
        key: _normalize_content_value(value)
        for key, value in item.items()
        if key not in _IGNORED_CONTENT_FIELDS
    }
    payload["__data_type"] = data_type
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _hash_text(canonical)


def prepare_dedup_record(data_type: str, item: dict[str, Any]) -> dict[str, Any]:
    prepared = dict(item)
    prepared["dedup_key"] = build_dedup_key(data_type, prepared)
    prepared["content_hash"] = build_content_hash(data_type, prepared)
    return prepared
