from __future__ import annotations

from datetime import date, datetime
from typing import Any

from crawler.parsers.pdf_parser import (
    extract_financial_highlights,
    extract_text_from_pdf_url,
    summarize_annual_report,
)


IMPORTANT_METRICS = (
    "营业总收入",
    "营业收入",
    "归母净利润",
    "净利润",
    "扣非净利润",
    "毛利率",
    "净资产收益率",
    "研发费用",
    "研发费用率",
    "基本每股收益",
    "每股收益",
)


def _normalize_stock_code(value: str | None, fallback: str = "") -> str:
    raw = str(value or fallback or "").strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits[-6:] if len(digits) >= 6 else digits


def _normalize_report_date(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()

    text = str(value).strip()
    if not text:
        return None

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue

    text = text.replace("/", "-")
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    if len(text) >= 10:
        return text[:10]
    return None


def _iter_report_date_keys(section: list[dict]) -> list[str]:
    keys: set[str] = set()
    for row in section:
        for key in row:
            key_text = str(key).strip()
            if len(key_text) == 8 and key_text.isdigit():
                keys.add(key_text)
    return sorted(keys)


def _latest_report_date_from_dataset(dataset: dict) -> str | None:
    candidates: list[str] = []

    for section_name in ("financial_abstract", "financial_indicators"):
        section = dataset.get(section_name) or []
        candidates.extend(_iter_report_date_keys(section))

    for section_name in ("balance_sheet", "profit_sheet", "cash_flow_sheet"):
        for row in dataset.get(section_name) or []:
            for key in ("报告期", "报表日期", "report_date", "REPORT_DATE"):
                normalized = _normalize_report_date(row.get(key))
                if normalized:
                    candidates.append(normalized.replace("-", ""))

    if not candidates:
        return None
    latest = max(candidates)
    return _normalize_report_date(latest)


def _format_metric_value(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def _build_metric_lines(section: list[dict], report_date_key: str) -> list[str]:
    preferred: list[str] = []
    fallback: list[str] = []

    for row in section:
        metric_name = str(row.get("指标") or row.get("metric_name") or "").strip()
        if not metric_name:
            continue
        value = row.get(report_date_key)
        if value in (None, ""):
            continue
        line = f"{metric_name}：{_format_metric_value(value)}"
        if metric_name in IMPORTANT_METRICS:
            preferred.append(line)
        elif len(fallback) < 6:
            fallback.append(line)

    lines = preferred or fallback
    return lines[:10]


def _find_pdf_urls(value: Any) -> list[str]:
    urls: list[str] = []

    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if "PDF" in key_text and isinstance(child, str) and child.startswith("http"):
                urls.append(child)
            urls.extend(_find_pdf_urls(child))
        return urls

    if isinstance(value, list):
        for child in value:
            urls.extend(_find_pdf_urls(child))
        return urls

    if isinstance(value, str) and value.startswith("http") and value.lower().endswith(".pdf"):
        urls.append(value)
    return urls


def _extract_pdf_summary(dataset: dict) -> tuple[str, str | None]:
    for pdf_url in _find_pdf_urls(dataset):
        try:
            text = extract_text_from_pdf_url(pdf_url, max_pages=10)
        except Exception:
            continue
        if not text.strip():
            continue

        summary = summarize_annual_report(text, max_chars=2000)
        highlights = extract_financial_highlights(text)
        parts = []
        if highlights:
            parts.append("财务指标摘录：")
            for key, value in highlights.items():
                parts.append(f"{key}：{value}")
        if summary:
            parts.append("报告摘要：")
            parts.append(summary)
        return "\n".join(parts).strip(), pdf_url
    return "", None


def extract_financial_note_text(dataset: dict, stock_code: str) -> str:
    normalized_stock_code = _normalize_stock_code(stock_code)
    company_name = str(dataset.get("name") or normalized_stock_code).strip()
    latest_report_date = _latest_report_date_from_dataset(dataset)
    report_date_key = latest_report_date.replace("-", "") if latest_report_date else ""

    parts: list[str] = []
    if company_name:
        parts.append(f"公司：{company_name}")
    if normalized_stock_code:
        parts.append(f"股票代码：{normalized_stock_code}")
    if latest_report_date:
        parts.append(f"报告期：{latest_report_date}")

    metric_lines: list[str] = []
    if report_date_key:
        metric_lines.extend(_build_metric_lines(dataset.get("financial_abstract") or [], report_date_key))
        if not metric_lines:
            metric_lines.extend(_build_metric_lines(dataset.get("financial_indicators") or [], report_date_key))

    if metric_lines:
        parts.append("财务摘要：")
        parts.extend(metric_lines)

    text = "\n".join(part for part in parts if part).strip()
    if text and metric_lines:
        return text

    pdf_summary, _ = _extract_pdf_summary(dataset)
    if pdf_summary:
        if text:
            return f"{text}\n\n{pdf_summary}".strip()
        return pdf_summary

    return text


def build_financial_notes_from_dataset(dataset: dict, stock_code: str) -> list[dict]:
    normalized_stock_code = _normalize_stock_code(stock_code)
    note_text = extract_financial_note_text(dataset, normalized_stock_code)
    if not note_text:
        return []

    report_date = _latest_report_date_from_dataset(dataset) or date.today().isoformat()
    note_type = "annual_report_summary" if report_date.endswith("12-31") else "periodic_report_summary"
    pdf_urls = _find_pdf_urls(dataset)
    source_url = pdf_urls[0] if pdf_urls else None

    return [
        {
            "stock_code": normalized_stock_code,
            "report_date": report_date,
            "note_type": note_type,
            "note_text": note_text,
            "note_json": {
                "report_date": report_date,
                "source_sections": [
                    section_name
                    for section_name in ("financial_abstract", "financial_indicators")
                    if dataset.get(section_name)
                ],
            },
            "source_type": "akshare_dataset",
            "source_url": source_url,
        }
    ]


def build_financial_package_payload(dataset: dict, stock_code: str, sync_vector_index: bool = True) -> dict:
    return {
        "income_statements": [],
        "balance_sheets": [],
        "cashflow_statements": [],
        "financial_metrics": [],
        "financial_notes": build_financial_notes_from_dataset(dataset, stock_code),
        "business_segments": [],
        "stock_daily": [],
        "sync_vector_index": bool(sync_vector_index),
    }
