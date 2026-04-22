from __future__ import annotations

from datetime import date, datetime
import hashlib


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


def _infer_exchange(dataset: dict, stock_code: str) -> str:
    exchange = str(dataset.get("exchange") or "").upper().strip()
    if exchange in {"SH", "SSE"}:
        return "SSE"
    if exchange in {"SZ", "SZSE"}:
        return "SZSE"
    if stock_code.startswith(("60", "68", "90")):
        return "SSE"
    if stock_code.startswith(("00", "20", "30")):
        return "SZSE"
    return exchange or "SSE"


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


def build_raw_announcements_from_dataset(dataset: dict, stock_code: str) -> list[dict]:
    normalized_stock_code = _normalize_stock_code(stock_code)
    exchange = _infer_exchange(dataset, normalized_stock_code)
    items: list[dict] = []

    for raw in dataset.get("announcements") or []:
        item_stock_code = _normalize_stock_code(raw.get("代码") or raw.get("stock_code"), normalized_stock_code)
        title = _pick_first(raw, "公告标题", "title")
        publish_date = _normalize_date(raw.get("公告日期") or raw.get("publish_date") or raw.get("date"))
        announcement_type = _pick_first(raw, "公告类型", "announcement_type") or "general"
        source_url = _pick_first(raw, "网址", "source_url", "url")
        source_type = _pick_first(raw, "source_type", "来源") or "akshare"
        content = _build_content(
            raw,
            title=title,
            announcement_type=announcement_type,
            publish_date=publish_date,
            source_url=source_url,
        )

        if not title:
            continue

        items.append(
            {
                "stock_code": item_stock_code,
                "title": title,
                "publish_date": publish_date,
                "announcement_type": announcement_type,
                "exchange": exchange,
                "content": content,
                "source_url": source_url,
                "source_type": source_type,
                "file_hash": hashlib.md5(f"{item_stock_code}|{title}|{publish_date or ''}|{source_url}".encode("utf-8")).hexdigest(),
            }
        )

    return items


def filter_announcement_items(items: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    for raw in items:
        stock_code = _normalize_stock_code(raw.get("stock_code"))
        title = str(raw.get("title") or "").strip()
        publish_date = _normalize_date(raw.get("publish_date"))
        content = str(raw.get("content") or "").strip()

        if not stock_code or not title or not content:
            continue

        dedupe_key = (stock_code, title, publish_date or "")
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        item = dict(raw)
        item["stock_code"] = stock_code
        item["title"] = title
        item["publish_date"] = publish_date
        item["content"] = content
        item["source_url"] = str(raw.get("source_url") or "").strip() or None
        item["source_type"] = str(raw.get("source_type") or "akshare").strip() or "akshare"
        item["announcement_type"] = str(raw.get("announcement_type") or "general").strip() or "general"
        item["exchange"] = str(raw.get("exchange") or "").strip() or _infer_exchange({}, stock_code)
        deduped.append(item)

    return deduped


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
