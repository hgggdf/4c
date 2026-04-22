from __future__ import annotations

from datetime import date, datetime
import hashlib


def _unwrap_dataset(dataset: dict | list | None) -> list[dict]:
    if isinstance(dataset, list):
        return [item for item in dataset if isinstance(item, dict)]
    if not isinstance(dataset, dict):
        return []
    if isinstance(dataset.get("items"), list):
        return [item for item in (dataset.get("items") or []) if isinstance(item, dict)]
    nested = dataset.get("data")
    if isinstance(nested, list):
        return [item for item in nested if isinstance(item, dict)]
    if isinstance(nested, dict) and isinstance(nested.get("items"), list):
        return [item for item in (nested.get("items") or []) if isinstance(item, dict)]
    return []


def _pick_first(item: dict, *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _normalize_stock_code(value: str | None) -> str | None:
    digits = "".join(ch for ch in str(value or "").strip() if ch.isdigit())
    if len(digits) >= 6:
        return digits[-6:]
    return digits or None


def _normalize_date(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace("/", "-").replace(".", "-")
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(normalized[:19], fmt).date().isoformat()
        except ValueError:
            continue

    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return None


def _normalize_publish_time(value) -> str | None:
    normalized_date = _normalize_date(value)
    if not normalized_date:
        return None
    return f"{normalized_date} 00:00:00"


def _normalize_source_name(item: dict) -> str:
    source_site = _pick_first(item, "source_site", "source_name", "source")
    if source_site:
        mapping = {
            "eastmoney": "东方财富研报",
            "dfcf": "东方财富研报",
        }
        return mapping.get(source_site.lower(), source_site)
    return "研报抓取"


def _normalize_news_type(item: dict) -> str:
    report_type = _pick_first(item, "report_type", "type").lower()
    if report_type == "industry":
        return "industry_research_report"
    if report_type == "stock":
        return "company_research_report"
    return "research_report"


def _build_report_content(item: dict, *, title: str, publish_date: str | None) -> str:
    existing = _pick_first(item, "content")
    if existing:
        return existing

    parts: list[str] = [title]
    stock_name = _pick_first(item, "stock_name", "stock")
    stock_code = _normalize_stock_code(_pick_first(item, "stock_code"))
    industry = _pick_first(item, "industry")
    org = _pick_first(item, "org", "author_name")
    rating = _pick_first(item, "rating")
    summary = _pick_first(item, "summary", "abstract")
    source_url = _pick_first(item, "source_url", "url")
    pdf_url = _pick_first(item, "pdf_url")

    if stock_name or stock_code:
        parts.append(f"标的：{stock_name or stock_code}")
    if stock_name and stock_code:
        parts[-1] = f"标的：{stock_name}({stock_code})"
    if industry:
        parts.append(f"行业：{industry}")
    if org:
        parts.append(f"机构：{org}")
    if publish_date:
        parts.append(f"发布日期：{publish_date}")
    if rating:
        parts.append(f"评级：{rating}")
    if summary:
        parts.append(f"摘要：{summary}")
    if source_url:
        parts.append(f"来源链接：{source_url}")
    if pdf_url:
        parts.append(f"PDF链接：{pdf_url}")
    return "\n".join(parts)


def _build_news_uid(item: dict, *, title: str, publish_date: str | None, source_url: str | None) -> str:
    report_type = _pick_first(item, "report_type", "type") or "report"
    stock_code = _normalize_stock_code(_pick_first(item, "stock_code")) or "industry"
    seed = f"{report_type}|{stock_code}|{title}|{publish_date or ''}|{source_url or ''}"
    return f"rr_{hashlib.md5(seed.encode('utf-8')).hexdigest()}"


def _build_file_hash(title: str, publish_date: str | None, source_url: str | None, pdf_url: str | None, content: str) -> str:
    seed = f"{title}|{publish_date or ''}|{source_url or pdf_url or ''}|{content[:120]}"
    return hashlib.md5(seed.encode("utf-8")).hexdigest()


def build_news_raw_from_report_dataset(dataset: dict | list) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    for raw in _unwrap_dataset(dataset):
        title = _pick_first(raw, "title")
        if not title:
            continue
        publish_date = _normalize_date(raw.get("publish_date") or raw.get("date"))
        source_url = _pick_first(raw, "source_url", "url") or None
        pdf_url = _pick_first(raw, "pdf_url") or None
        content = _build_report_content(raw, title=title, publish_date=publish_date)
        news_uid = _build_news_uid(raw, title=title, publish_date=publish_date, source_url=source_url or pdf_url)
        if news_uid in seen:
            continue
        seen.add(news_uid)
        items.append(
            {
                "news_uid": news_uid,
                "title": title,
                "publish_time": _normalize_publish_time(publish_date),
                "source_name": _normalize_source_name(raw),
                "source_url": source_url or pdf_url,
                "author_name": _pick_first(raw, "org", "author_name") or None,
                "content": content,
                "news_type": _normalize_news_type(raw),
                "language": "zh",
                "file_hash": _build_file_hash(title, publish_date, source_url, pdf_url, content),
            }
        )
    return items


def build_research_report_news_package_payload(dataset: dict | list, sync_vector_index: bool = True) -> dict:
    return {
        "macro_indicators": [],
        "news_raw": build_news_raw_from_report_dataset(dataset),
        "news_structured": [],
        "news_industry_maps": {},
        "news_company_maps": {},
        "industry_impact_events": [],
        "sync_vector_index": bool(sync_vector_index),
    }


def build_news_package_payload(dataset: dict | list, sync_vector_index: bool = True) -> dict:
    return build_research_report_news_package_payload(dataset, sync_vector_index=sync_vector_index)


__all__ = [
    "build_news_package_payload",
    "build_news_raw_from_report_dataset",
    "build_research_report_news_package_payload",
]