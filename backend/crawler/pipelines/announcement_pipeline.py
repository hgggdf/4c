from __future__ import annotations

from datetime import date, datetime
import hashlib


SOURCE_PRIORITY = {
    "sse_announcement_api": 50,
    "szse_announcement_api": 50,
    "bse_announcement_api": 50,
    "exchange_announcement_api": 48,
    "eastmoney_announcement_api": 40,
    "eastmoney_announcement_html": 35,
    "akshare": 20,
    "crawler": 15,
    "local_sample": 10,
}


def _unwrap_dataset(dataset: dict | list | None) -> tuple[dict, list[dict]]:
    if isinstance(dataset, list):
        return {}, [item for item in dataset if isinstance(item, dict)]
    if not isinstance(dataset, dict):
        return {}, []

    if isinstance(dataset.get("items"), list):
        return dataset, [item for item in (dataset.get("items") or []) if isinstance(item, dict)]
    if isinstance(dataset.get("announcements"), list):
        return dataset, [item for item in (dataset.get("announcements") or []) if isinstance(item, dict)]

    nested = dataset.get("data")
    if isinstance(nested, list):
        return dataset, [item for item in nested if isinstance(item, dict)]
    if isinstance(nested, dict):
        if isinstance(nested.get("items"), list):
            return nested, [item for item in (nested.get("items") or []) if isinstance(item, dict)]
        if isinstance(nested.get("announcements"), list):
            return nested, [item for item in (nested.get("announcements") or []) if isinstance(item, dict)]

    return dataset, []


def _normalize_stock_code(value: str | None, fallback: str = "") -> str:
    raw = str(value or fallback or "").strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits[-6:] if len(digits) >= 6 else digits


def _normalize_date(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()

    text = str(value).strip()
    if not text:
        return None

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue

    text = text.replace(".", "-").replace("/", "-")
    if len(text) >= 10:
        return text[:10]
    return None


def _pick_first(item: dict, *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _normalize_exchange(value: str | None) -> str:
    exchange = str(value or "").upper().strip()
    if exchange in {"SH", "SSE"}:
        return "SSE"
    if exchange in {"SZ", "SZSE"}:
        return "SZSE"
    if exchange in {"BJ", "BSE", "NEEQ"}:
        return "BSE"
    return exchange


def _infer_exchange(dataset: dict, stock_code: str, item: dict | None = None) -> str:
    exchange = _normalize_exchange(_pick_first(item or {}, "exchange", "交易所") or dataset.get("exchange") or dataset.get("market"))
    if exchange:
        return exchange

    source = str(dataset.get("source") or "").upper().strip()
    if source in {"SSE", "SH", "SSE.COM.CN"}:
        return "SSE"
    if source in {"SZSE", "SZ"}:
        return "SZSE"
    if source in {"BSE", "BJ"}:
        return "BSE"

    if stock_code.startswith(("60", "68", "90")):
        return "SSE"
    if stock_code.startswith(("00", "20", "30")):
        return "SZSE"
    if stock_code.startswith(("43", "83", "87", "92")):
        return "BSE"
    return "SSE"


def _normalize_source_type(item: dict, dataset: dict) -> str:
    raw = _pick_first(item, "source_type", "来源")
    if raw:
        return raw[:32]

    source = str(dataset.get("source") or "crawler").strip().lower() or "crawler"
    strategy = str(dataset.get("strategy") or "").strip().lower().replace("/", "_")
    derived = f"{source}_{strategy}".strip("_")
    return (derived or "crawler")[:32]


def _normalize_announcement_type(item: dict) -> str:
    announcement_type = _pick_first(item, "announcement_type", "公告类型", "column_name", "category")
    return announcement_type or "公告"


def _item_hash(stock_code: str, title: str, publish_date: str | None, source_url: str | None, content: str | None) -> str:
    source_part = source_url or (content or "")[:120]
    raw = f"{stock_code}|{title}|{publish_date or ''}|{source_part}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _build_content(item: dict, *, title: str, announcement_type: str, publish_date: str | None, source_url: str) -> str:
    existing = _pick_first(
        item,
        "content",
        "公告内容",
        "正文",
        "摘要",
        "summary",
        "内容",
        "detail",
    )
    if existing:
        return existing

    parts = [title]
    if announcement_type:
        parts.append(f"公告类型：{announcement_type}")
    if publish_date:
        parts.append(f"公告日期：{publish_date}")
    if source_url:
        parts.append(f"来源链接：{source_url}")
    return "\n".join(parts)


def build_raw_announcements_from_dataset(dataset: dict | list, stock_code: str) -> list[dict]:
    dataset_meta, rows = _unwrap_dataset(dataset)
    normalized_stock_code = _normalize_stock_code(stock_code)
    items: list[dict] = []

    for raw in rows:
        item_stock_code = _normalize_stock_code(
            raw.get("代码") or raw.get("stock_code") or raw.get("symbol"),
            normalized_stock_code,
        )
        title = _pick_first(raw, "公告标题", "title", "notice_title", "name")
        publish_date = _normalize_date(raw.get("公告日期") or raw.get("publish_date") or raw.get("date") or raw.get("notice_date"))
        announcement_type = _normalize_announcement_type(raw)
        source_url = _pick_first(raw, "网址", "source_url", "url", "pdf_url", "URL")
        source_type = _normalize_source_type(raw, dataset_meta)
        exchange = _infer_exchange(dataset_meta, item_stock_code, raw)
        content = _build_content(
            raw,
            title=title,
            announcement_type=announcement_type,
            publish_date=publish_date,
            source_url=source_url,
        )

        if not item_stock_code or not title:
            continue

        items.append(
            {
                "stock_code": item_stock_code,
                "title": title,
                "publish_date": publish_date,
                "announcement_type": announcement_type,
                "exchange": exchange,
                "content": content,
                "source_url": source_url or None,
                "source_type": source_type,
                "file_hash": _pick_first(raw, "file_hash") or _item_hash(item_stock_code, title, publish_date, source_url or None, content),
            }
        )

    return items


def _source_priority(source_type: str | None) -> int:
    normalized = str(source_type or "").strip().lower()
    if normalized in SOURCE_PRIORITY:
        return SOURCE_PRIORITY[normalized]
    if "official" in normalized or normalized.startswith(("sse_", "szse_", "bse_")):
        return 45
    if "eastmoney" in normalized:
        return 38
    if "sample" in normalized:
        return 10
    return 0


def _merge_preferred(existing: dict, candidate: dict) -> dict:
    existing_score = _source_priority(existing.get("source_type"))
    candidate_score = _source_priority(candidate.get("source_type"))
    if candidate_score > existing_score:
        preferred, fallback = dict(candidate), existing
    elif candidate_score < existing_score:
        preferred, fallback = dict(existing), candidate
    else:
        preferred = dict(existing)
        fallback = candidate
        if len(str(candidate.get("content") or "")) > len(str(existing.get("content") or "")):
            preferred = dict(candidate)
            fallback = existing
        elif not preferred.get("source_url") and candidate.get("source_url"):
            preferred = dict(candidate)
            fallback = existing

    for key in ("content", "source_url", "source_type", "exchange", "announcement_type"):
        if not preferred.get(key) and fallback.get(key):
            preferred[key] = fallback.get(key)

    preferred["file_hash"] = _item_hash(
        preferred.get("stock_code") or fallback.get("stock_code") or "",
        preferred.get("title") or fallback.get("title") or "",
        preferred.get("publish_date") or fallback.get("publish_date"),
        preferred.get("source_url") or fallback.get("source_url"),
        preferred.get("content") or fallback.get("content"),
    )
    return preferred


def filter_announcement_items(items: list[dict]) -> list[dict]:
    deduped: dict[tuple[str, str, str], dict] = {}

    for raw in items:
        stock_code = _normalize_stock_code(raw.get("stock_code"))
        title = str(raw.get("title") or "").strip()
        publish_date = _normalize_date(raw.get("publish_date"))
        content = str(raw.get("content") or "").strip()

        if not stock_code or not title or not content:
            continue

        dedupe_key = (stock_code, title, publish_date or "")
        item = dict(raw)
        item["stock_code"] = stock_code
        item["title"] = title
        item["publish_date"] = publish_date
        item["content"] = content
        item["source_url"] = str(raw.get("source_url") or "").strip() or None
        item["source_type"] = str(raw.get("source_type") or "crawler").strip()[:32] or "crawler"
        item["announcement_type"] = str(raw.get("announcement_type") or "公告").strip() or "公告"
        item["exchange"] = _normalize_exchange(raw.get("exchange")) or _infer_exchange({}, stock_code)
        item["file_hash"] = str(raw.get("file_hash") or "").strip() or _item_hash(stock_code, title, publish_date, item.get("source_url"), content)

        if dedupe_key in deduped:
            deduped[dedupe_key] = _merge_preferred(deduped[dedupe_key], item)
        else:
            deduped[dedupe_key] = item

    return list(deduped.values())


def build_announcement_package_payload(dataset: dict, stock_code: str, sync_vector_index: bool = True) -> dict:
    raw_announcements = filter_announcement_items(
        build_raw_announcements_from_dataset(dataset, stock_code)
    )
    return {
        "raw_announcements": raw_announcements,
        "structured_announcements": [],
        "drug_approvals": [],
        "clinical_trials": [],
        "procurement_events": [],
        "regulatory_risks": [],
        "sync_vector_index": bool(sync_vector_index),
    }
