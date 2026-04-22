from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from crawler.parsers.pdf_parser import extract_financial_highlights, extract_text_from_pdf_url, summarize_annual_report


IMPORTANT_METRICS = (
    "营业总收入",
    "营业收入",
    "归母净利润",
    "归属于母公司所有者的净利润",
    "净利润",
    "扣非净利润",
    "毛利率",
    "净资产收益率",
    "研发费用",
    "研发费用率",
    "基本每股收益",
    "每股收益",
)


def _unwrap_bundle(dataset: dict) -> dict:
    if isinstance(dataset, dict) and isinstance(dataset.get("data"), dict):
        return dataset.get("data") or {}
    return dataset or {}


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


def _report_date_from_any(value) -> str | None:
    return _normalize_date(value)


def _report_type_from_row(row: dict, report_date: str | None = None) -> str:
    text = " ".join(str(row.get(key) or "") for key in ("类型", "report_type", "REPORT_TYPE", "公告类型", "BULLETIN_TYPE_DESC")).strip()
    text_lower = text.lower()
    if any(token in text for token in ("一季", "第一季度")) or "q1" in text_lower:
        return "q1"
    if any(token in text for token in ("半年", "中报", "半年度")) or "q2" in text_lower:
        return "semiannual"
    if any(token in text for token in ("三季", "第三季度")) or "q3" in text_lower:
        return "q3"
    if any(token in text for token in ("年度", "年报")) or "annual" in text_lower:
        return "annual"
    if report_date and report_date.endswith("-03-31"):
        return "q1"
    if report_date and report_date.endswith("-06-30"):
        return "semiannual"
    if report_date and report_date.endswith("-09-30"):
        return "q3"
    if report_date and report_date.endswith("-12-31"):
        return "annual"
    return "periodic"


def _coerce_number(value) -> float | None:
    if value in (None, "", "--"):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").replace("%", "").strip()
    if not text:
        return None
    try:
        return float(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def _text_or_none(value) -> str | None:
    text = " ".join(str(value or "").split())
    return text or None


def _dedupe_items(items: list[dict], keys: tuple[str, ...]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[tuple] = set()
    for item in items:
        key = tuple(item.get(name) for name in keys)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _iter_report_date_keys(section: list[dict]) -> list[str]:
    keys: set[str] = set()
    for row in section:
        for key in row:
            key_text = str(key).strip()
            if len(key_text) == 8 and key_text.isdigit():
                keys.add(key_text)
    return sorted(keys, reverse=True)


def _latest_report_date_from_dataset(dataset: dict) -> str | None:
    candidates: list[str] = []
    bundle = _unwrap_bundle(dataset)

    for section_name in ("financial_abstract", "financial_indicators"):
        candidates.extend(_iter_report_date_keys(bundle.get(section_name) or []))

    for section_name in ("income_statements_raw", "balance_sheets_raw", "cashflow_statements_raw"):
        for row in bundle.get(section_name) or []:
            normalized = _normalize_date(row.get("报告日") or row.get("报告日期") or row.get("report_date"))
            if normalized:
                candidates.append(normalized.replace("-", ""))

    if not candidates:
        return None
    return _normalize_date(max(candidates))


def _build_metric_lines(section: list[dict], report_date_key: str) -> list[str]:
    preferred: list[str] = []
    fallback: list[str] = []
    for row in section:
        metric_name = _text_or_none(row.get("指标") or row.get("metric_name"))
        if not metric_name:
            continue
        value = row.get(report_date_key)
        if value in (None, ""):
            continue
        line = f"{metric_name}：{value}"
        if metric_name in IMPORTANT_METRICS:
            preferred.append(line)
        elif len(fallback) < 6:
            fallback.append(line)
    return (preferred or fallback)[:10]


def _find_pdf_urls(value: Any) -> list[str]:
    urls: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if "PDF" in str(key) and isinstance(child, str) and child.startswith("http"):
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
        parts: list[str] = []
        if highlights:
            parts.append("财务指标摘录：")
            for key, value in highlights.items():
                parts.append(f"{key}：{value}")
        if summary:
            parts.append("报告摘要：")
            parts.append(summary)
        return "\n".join(parts).strip(), pdf_url
    return "", None


def _lookup_abstract_value(bundle: dict, metric_name: str, report_date: str) -> float | None:
    report_key = report_date.replace("-", "")
    for row in bundle.get("financial_abstract") or []:
        if _text_or_none(row.get("指标")) == metric_name:
            return _coerce_number(row.get(report_key))
    return None


def _metric_unit(metric_name: str) -> str | None:
    if any(token in metric_name for token in ("率", "ROE", "ROA", "毛利率", "净利率")):
        return "ratio"
    if any(token in metric_name for token in ("每股", "EPS")):
        return "per_share"
    return None


def extract_financial_note_text(dataset: dict, stock_code: str) -> str:
    bundle = _unwrap_bundle(dataset)
    normalized_stock_code = _normalize_stock_code(stock_code)
    company_name = _text_or_none(bundle.get("name")) or normalized_stock_code
    latest_report_date = _latest_report_date_from_dataset(bundle)
    report_date_key = latest_report_date.replace("-", "") if latest_report_date else ""

    parts: list[str] = []
    if company_name:
        parts.append(f"公司：{company_name}")
    if normalized_stock_code:
        parts.append(f"股票代码：{normalized_stock_code}")
    if latest_report_date:
        parts.append(f"报告期：{latest_report_date}")

    metric_lines = _build_metric_lines(bundle.get("financial_abstract") or [], report_date_key) if report_date_key else []
    if metric_lines:
        parts.append("财务摘要：")
        parts.extend(metric_lines)

    text = "\n".join(part for part in parts if part).strip()
    if text and metric_lines:
        return text

    pdf_summary, _ = _extract_pdf_summary(bundle)
    if pdf_summary:
        return f"{text}\n\n{pdf_summary}".strip() if text else pdf_summary
    return text


def build_financial_notes_from_dataset(dataset: dict, stock_code: str) -> list[dict]:
    bundle = _unwrap_bundle(dataset)
    normalized_stock_code = _normalize_stock_code(stock_code)
    note_text = extract_financial_note_text(bundle, normalized_stock_code)
    if not note_text:
        return []
    report_date = _latest_report_date_from_dataset(bundle) or date.today().isoformat()
    note_type = "annual_report_summary" if report_date.endswith("12-31") else "periodic_report_summary"
    pdf_urls = _find_pdf_urls(bundle)
    source_refs = bundle.get("source_refs") or {}
    source_url = pdf_urls[0] if pdf_urls else source_refs.get("financial_abstract")
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
                    for section_name in ("financial_abstract", "financial_indicators", "income_statements_raw")
                    if bundle.get(section_name)
                ],
            },
            "source_type": "crawler_financial_bundle",
            "source_url": source_url,
        }
    ]


def build_income_statements_from_dataset(dataset: dict, stock_code: str, *, limit: int = 8) -> list[dict]:
    bundle = _unwrap_bundle(dataset)
    source_url = (bundle.get("source_refs") or {}).get("income_statements_raw")
    items: list[dict] = []
    for row in (bundle.get("income_statements_raw") or [])[: max(limit, 1)]:
        report_date = _report_date_from_any(row.get("报告日") or row.get("报告日期") or row.get("report_date"))
        if not report_date:
            continue
        revenue = _coerce_number(row.get("营业总收入") or row.get("营业收入"))
        operating_cost = _coerce_number(row.get("营业成本"))
        gross_profit = _coerce_number(row.get("毛利"))
        if gross_profit is None and revenue is not None and operating_cost is not None:
            gross_profit = revenue - operating_cost
        items.append(
            {
                "stock_code": _normalize_stock_code(stock_code),
                "report_date": report_date,
                "fiscal_year": int(report_date[:4]),
                "report_type": _report_type_from_row(row, report_date),
                "revenue": revenue,
                "operating_cost": operating_cost,
                "gross_profit": gross_profit,
                "selling_expense": _coerce_number(row.get("销售费用")),
                "admin_expense": _coerce_number(row.get("管理费用")),
                "rd_expense": _coerce_number(row.get("研发费用")),
                "operating_profit": _coerce_number(row.get("营业利润")),
                "net_profit": _coerce_number(row.get("归属于母公司所有者的净利润") or row.get("净利润")),
                "net_profit_deducted": _lookup_abstract_value(bundle, "扣非净利润", report_date),
                "eps": _coerce_number(row.get("基本每股收益") or row.get("每股收益")),
                "source_type": "crawler_financial_bundle",
                "source_url": source_url,
            }
        )
    return _dedupe_items(items, ("stock_code", "report_date", "report_type"))


def build_balance_sheets_from_dataset(dataset: dict, stock_code: str, *, limit: int = 8) -> list[dict]:
    bundle = _unwrap_bundle(dataset)
    source_url = (bundle.get("source_refs") or {}).get("balance_sheets_raw")
    items: list[dict] = []
    for row in (bundle.get("balance_sheets_raw") or [])[: max(limit, 1)]:
        report_date = _report_date_from_any(row.get("报告日") or row.get("报告日期") or row.get("report_date"))
        if not report_date:
            continue
        items.append(
            {
                "stock_code": _normalize_stock_code(stock_code),
                "report_date": report_date,
                "fiscal_year": int(report_date[:4]),
                "report_type": _report_type_from_row(row, report_date),
                "total_assets": _coerce_number(row.get("资产总计") or row.get("total_assets")),
                "total_liabilities": _coerce_number(row.get("负债合计") or row.get("total_liabilities")),
                "accounts_receivable": _coerce_number(row.get("应收账款") or row.get("应收票据及应收账款")),
                "inventory": _coerce_number(row.get("存货")),
                "cash": _coerce_number(row.get("货币资金") or row.get("现金")),
                "equity": _coerce_number(row.get("归属于母公司股东权益合计") or row.get("所有者权益(或股东权益)合计")),
                "goodwill": _coerce_number(row.get("商誉")),
                "source_type": "crawler_financial_bundle",
                "source_url": source_url,
            }
        )
    return _dedupe_items(items, ("stock_code", "report_date", "report_type"))


def build_cashflow_statements_from_dataset(dataset: dict, stock_code: str, *, limit: int = 8) -> list[dict]:
    bundle = _unwrap_bundle(dataset)
    source_url = (bundle.get("source_refs") or {}).get("cashflow_statements_raw")
    items: list[dict] = []
    for row in (bundle.get("cashflow_statements_raw") or [])[: max(limit, 1)]:
        report_date = _report_date_from_any(row.get("报告日") or row.get("报告日期") or row.get("report_date"))
        if not report_date:
            continue
        operating = _coerce_number(row.get("经营活动产生的现金流量净额"))
        investing = _coerce_number(row.get("投资活动产生的现金流量净额"))
        financing = _coerce_number(row.get("筹资活动产生的现金流量净额"))
        items.append(
            {
                "stock_code": _normalize_stock_code(stock_code),
                "report_date": report_date,
                "fiscal_year": int(report_date[:4]),
                "report_type": _report_type_from_row(row, report_date),
                "operating_cashflow": operating,
                "investing_cashflow": investing,
                "financing_cashflow": financing,
                "free_cashflow": (operating + investing) if operating is not None and investing is not None else None,
                "source_type": "crawler_financial_bundle",
                "source_url": source_url,
            }
        )
    return _dedupe_items(items, ("stock_code", "report_date", "report_type"))


def build_financial_metrics_from_dataset(dataset: dict, stock_code: str, *, max_periods: int = 4, max_metrics: int = 24) -> list[dict]:
    bundle = _unwrap_bundle(dataset)
    source_url = (bundle.get("source_refs") or {}).get("financial_abstract")
    period_keys = _iter_report_date_keys(bundle.get("financial_abstract") or [])[: max(max_periods, 1)]
    items: list[dict] = []
    for row in bundle.get("financial_abstract") or []:
        metric_name = _text_or_none(row.get("指标"))
        if not metric_name:
            continue
        for period_key in period_keys:
            metric_value = _coerce_number(row.get(period_key))
            if metric_value is None:
                continue
            report_date = _normalize_date(period_key)
            if not report_date:
                continue
            items.append(
                {
                    "stock_code": _normalize_stock_code(stock_code),
                    "report_date": report_date,
                    "fiscal_year": int(report_date[:4]),
                    "metric_name": metric_name,
                    "metric_value": metric_value,
                    "metric_unit": _metric_unit(metric_name),
                    "calc_method": row.get("选项") or "source_extract",
                    "source_ref_json": {
                        "source": "financial_abstract",
                        "report_key": period_key,
                        "source_url": source_url,
                    },
                }
            )
            if len(items) >= max_metrics:
                break
        if len(items) >= max_metrics:
            break

    if not items:
        for row in bundle.get("financial_indicators") or []:
            report_date = _report_date_from_any(row.get("REPORT_DATE") or row.get("report_date"))
            if not report_date:
                continue
            for key, value in row.items():
                if key in {"REPORT_DATE", "SECUCODE", "SECURITY_CODE", "SECURITY_NAME_ABBR", "NOTICE_DATE"}:
                    continue
                metric_value = _coerce_number(value)
                if metric_value is None:
                    continue
                items.append(
                    {
                        "stock_code": _normalize_stock_code(stock_code),
                        "report_date": report_date,
                        "fiscal_year": int(report_date[:4]),
                        "metric_name": str(key),
                        "metric_value": metric_value,
                        "metric_unit": _metric_unit(str(key)),
                        "calc_method": "source_extract",
                        "source_ref_json": {
                            "source": "financial_indicators",
                            "report_key": report_date,
                            "source_url": source_url,
                        },
                    }
                )
                if len(items) >= max_metrics:
                    break
            if len(items) >= max_metrics:
                break
    return _dedupe_items(items, ("stock_code", "report_date", "metric_name"))


def build_business_segments_from_dataset(dataset: dict, stock_code: str, *, limit: int = 20) -> list[dict]:
    bundle = _unwrap_bundle(dataset)
    source_url = (bundle.get("source_refs") or {}).get("business_segments_raw")
    items: list[dict] = []
    for row in (bundle.get("business_segments_raw") or [])[: max(limit, 1)]:
        report_date = _report_date_from_any(row.get("报告日期") or row.get("report_date"))
        segment_name = _text_or_none(row.get("主营构成") or row.get("segment_name"))
        if not report_date or not segment_name:
            continue
        items.append(
            {
                "stock_code": _normalize_stock_code(stock_code),
                "report_date": report_date,
                "segment_name": segment_name,
                "segment_type": _text_or_none(row.get("分类类型") or row.get("segment_type")) or "segment",
                "revenue": _coerce_number(row.get("主营收入") or row.get("revenue")),
                "revenue_ratio": _coerce_number(row.get("收入比例") or row.get("revenue_ratio")),
                "gross_margin": _coerce_number(row.get("毛利率") or row.get("毛利 率") or row.get("gross_margin")),
                "source_type": "crawler_financial_bundle",
                "source_url": source_url,
            }
        )
    return _dedupe_items(items, ("stock_code", "report_date", "segment_name", "segment_type"))


def build_stock_daily_from_dataset(dataset: dict, stock_code: str, *, limit: int = 60) -> list[dict]:
    bundle = _unwrap_bundle(dataset)
    rows = (bundle.get("stock_daily_raw") or bundle.get("kline") or [])[: max(limit, 1)]
    items: list[dict] = []
    for row in rows:
        trade_date = _report_date_from_any(row.get("日期") or row.get("date") or row.get("trade_date"))
        if not trade_date:
            continue
        volume = _coerce_number(row.get("成交量") or row.get("volume"))
        items.append(
            {
                "stock_code": _normalize_stock_code(stock_code),
                "trade_date": trade_date,
                "open_price": _coerce_number(row.get("开盘") or row.get("open")),
                "close_price": _coerce_number(row.get("收盘") or row.get("close")),
                "high_price": _coerce_number(row.get("最高") or row.get("high")),
                "low_price": _coerce_number(row.get("最低") or row.get("low")),
                "volume": int(volume) if volume is not None else None,
                "turnover": _coerce_number(row.get("成交额") or row.get("turnover")),
                "source_type": "crawler_financial_bundle",
            }
        )
    return _dedupe_items(items, ("stock_code", "trade_date"))


def build_financial_package_payload(dataset: dict, stock_code: str, sync_vector_index: bool = True) -> dict:
    bundle = _unwrap_bundle(dataset)
    normalized_stock_code = _normalize_stock_code(stock_code or bundle.get("stock_code"))
    return {
        "income_statements": build_income_statements_from_dataset(bundle, normalized_stock_code),
        "balance_sheets": build_balance_sheets_from_dataset(bundle, normalized_stock_code),
        "cashflow_statements": build_cashflow_statements_from_dataset(bundle, normalized_stock_code),
        "financial_metrics": build_financial_metrics_from_dataset(bundle, normalized_stock_code),
        "financial_notes": build_financial_notes_from_dataset(bundle, normalized_stock_code),
        "business_segments": build_business_segments_from_dataset(bundle, normalized_stock_code),
        "stock_daily": build_stock_daily_from_dataset(bundle, normalized_stock_code),
        "sync_vector_index": bool(sync_vector_index),
    }


__all__ = [
    "build_balance_sheets_from_dataset",
    "build_business_segments_from_dataset",
    "build_cashflow_statements_from_dataset",
    "build_financial_metrics_from_dataset",
    "build_financial_notes_from_dataset",
    "build_financial_package_payload",
    "build_income_statements_from_dataset",
    "build_stock_daily_from_dataset",
    "extract_financial_note_text",
]