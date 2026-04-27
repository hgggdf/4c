from __future__ import annotations

import re
from typing import Any


KNOWN_COMPANY_NAMES = [
    "中国生物制药",
    "恒瑞医药",
    "复星医药",
    "以岭药业",
    "药明康德",
    "百济神州",
    "迈瑞医疗",
    "华东医药",
    "科伦药业",
    "长春高新",
    "智飞生物",
    "沃森生物",
    "康希诺",
    "君实生物",
    "信达生物",
    "康方生物",
    "石药集团",
]

COMPANY_SUFFIXES = ("医药", "生物", "药业", "制药", "股份", "医疗", "科技", "高新", "集团")

TIME_RANGE_PATTERNS: list[tuple[re.Pattern[str], dict[str, Any]]] = [
    (re.compile(r"(今天|今日)"), {"type": "relative", "value": "today"}),
    (re.compile(r"(最近|近期)"), {"type": "relative", "value": "recent"}),
    (re.compile(r"本周"), {"type": "relative", "value": "this_week"}),
    (re.compile(r"本月"), {"type": "relative", "value": "this_month"}),
    (re.compile(r"本季度"), {"type": "relative", "value": "this_quarter"}),
    (re.compile(r"(今年|本年)"), {"type": "relative", "value": "this_year"}),
    (re.compile(r"去年"), {"type": "relative", "value": "last_year"}),
    (re.compile(r"近一年"), {"type": "relative", "value": "last_1_year"}),
    (re.compile(r"近三年|三年"), {"type": "relative", "value": "last_3_years"}),
    (re.compile(r"近五年|五年"), {"type": "relative", "value": "last_5_years"}),
    (re.compile(r"(20\d{2})\s*[Qq]([1-4])"), {"type": "quarter"}),
    (re.compile(r"(20\d{2})年年报"), {"type": "year_report"}),
    (re.compile(r"(20\d{2})年"), {"type": "year"}),
    (re.compile(r"(20\d{2})"), {"type": "year"}),
]

DRUG_HINTS = [
    "药品",
    "新药",
    "管线",
    "临床试验",
    "临床",
    "适应症",
    "获批",
    "IND",
    "NDA",
    "BLA",
    "一期",
    "二期",
    "三期",
    "创新药",
    "注射液",
    "片",
    "胶囊",
    "抗体",
    "单抗",
    "双抗",
    "ADC",
    "PD-1",
    "GLP-1",
]

INDUSTRY_KEYWORDS = [
    "医药",
    "创新药",
    "仿制药",
    "CXO",
    "CRO",
    "CDMO",
    "医疗器械",
    "中药",
    "生物药",
    "化学制药",
    "疫苗",
    "IVD",
    "药店",
    "医疗服务",
    "医保",
    "集采",
]

REFERENCE_PRONOUNS = ["这家公司", "该公司", "这个公司", "这家企业", "该企业", "这个标的", "该标的", "它的", "它", "其"]


def extract_stock_code(text: str) -> str | None:
    match = re.search(r"(?<!\d)(\d{6})(?!\d)", str(text or ""))
    return match.group(1) if match else None


def extract_time_range(text: str) -> dict[str, Any] | None:
    source = str(text or "")
    quarter_match = re.search(r"(20\d{2})\s*[Qq]([1-4])", source)
    if quarter_match:
        year, quarter = quarter_match.group(1), quarter_match.group(2)
        return {"raw": quarter_match.group(0), "type": "quarter", "value": f"quarter_{year}_q{quarter.lower()}"}

    year_report_match = re.search(r"(20\d{2})年年报", source)
    if year_report_match:
        year = year_report_match.group(1)
        return {"raw": year_report_match.group(0), "type": "year_report", "value": f"year_{year}"}

    for pattern, payload in TIME_RANGE_PATTERNS:
        if payload["type"] == "quarter" or payload["type"] == "year_report":
            continue
        match = pattern.search(source)
        if not match:
            continue
        if payload["type"] == "year":
            year = match.group(1)
            return {"raw": match.group(0), "type": "year", "value": f"year_{year}"}
        return {"raw": match.group(0), **payload}
    return None


def _find_known_company_name(text: str) -> str | None:
    source = str(text or "")
    for name in sorted(KNOWN_COMPANY_NAMES, key=len, reverse=True):
        if name in source:
            return name
    return None


def extract_company_name(text: str) -> str | None:
    source = str(text or "")
    known = _find_known_company_name(source)
    if known:
        return known

    patterns = [
        r"([\u4e00-\u9fff]{2,12}(?:医药|生物|药业|制药|股份|医疗|科技|高新|集团))",
        r"([\u4e00-\u9fff]{2,12}药)"
    ]
    for pattern in patterns:
        match = re.search(pattern, source)
        if match:
            candidate = match.group(1)
            if candidate not in KNOWN_COMPANY_NAMES and len(candidate) >= 3:
                return candidate
    return None


def extract_drug_entity(text: str) -> dict[str, Any] | None:
    source = str(text or "")
    lowered = source.lower()
    hit = None
    for keyword in sorted(DRUG_HINTS, key=len, reverse=True):
        if keyword.lower() in lowered:
            hit = keyword
            break
    if not hit:
        return None

    name = None
    for token in ("PD-1", "GLP-1", "ADC"):
        if token.lower() in lowered:
            name = token
            break

    return {
        "name": name,
        "raw": hit,
        "confidence": "low",
        "source": "rule",
        "need_clarification": True,
    }


def extract_industry_entity(text: str) -> dict[str, Any] | None:
    source = str(text or "")
    lowered = source.lower()
    for keyword in INDUSTRY_KEYWORDS:
        if keyword.isascii():
            if keyword.lower() in lowered:
                return {"name": keyword.upper() if keyword in {"cxo", "cro", "cdmo", "ivd"} else keyword, "raw": keyword, "confidence": "medium", "source": "rule"}
        elif keyword in source:
            return {"name": keyword, "raw": keyword, "confidence": "medium", "source": "rule"}
    return None


def infer_company_from_targets(targets: list[dict[str, Any]]) -> dict[str, Any] | None:
    for target in targets or []:
        if str(target.get("type") or "").strip() != "stock":
            continue
        stock_code = str(target.get("symbol") or "").strip() or None
        company_name = str(target.get("name") or "").strip() or None
        result: dict[str, Any] = {"source": "targets", "confidence": "high"}
        if company_name:
            result["company_name"] = company_name
        if stock_code:
            result["stock_code"] = stock_code
        if result.get("company_name") or result.get("stock_code"):
            return result
    return None


def infer_company_from_context(current_stock_code: str | None) -> dict[str, Any] | None:
    if not current_stock_code:
        return None
    return {"company_name": None, "stock_code": current_stock_code, "source": "current_stock_code", "confidence": "medium"}


def infer_company_from_history(history: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in reversed(history or []):
        content = str(item.get("content") or item.get("question") or item.get("answer") or "")
        stock_code = extract_stock_code(content)
        company_name = extract_company_name(content)
        if stock_code or company_name:
            return {
                "company_name": company_name,
                "stock_code": stock_code,
                "source": "history",
                "confidence": "medium",
            }
    return None


def has_reference_pronoun(text: str) -> bool:
    source = str(text or "")
    return any(pronoun in source for pronoun in REFERENCE_PRONOUNS)


def resolve_entities(
    user_question: str,
    history: list[dict[str, Any]] | None = None,
    targets: list[dict[str, Any]] | None = None,
    current_stock_code: str | None = None,
) -> dict[str, Any]:
    question = str(user_question or "")
    entity_result: dict[str, Any] = {
        "company_entity": None,
        "drug_entity": extract_drug_entity(question),
        "industry_entity": extract_industry_entity(question),
        "time_range": extract_time_range(question),
        "warnings": [],
    }

    company_entity = infer_company_from_targets(list(targets or []))
    if company_entity is None:
        stock_code = extract_stock_code(question)
        company_name = extract_company_name(question)
        if stock_code or company_name:
            company_entity = {
                "company_name": company_name,
                "stock_code": stock_code,
                "source": "question",
                "confidence": "high",
            }

    reference_hit = has_reference_pronoun(question)
    if company_entity is None:
        company_entity = infer_company_from_context(current_stock_code)
    if company_entity is None and reference_hit:
        company_entity = infer_company_from_history(list(history or []))
        if company_entity is None:
            entity_result["warnings"].append(
                {
                    "type": "指代不明确",
                    "message": "无法确认当前问题中的指代对象",
                    "detail": {},
                }
            )

    entity_result["company_entity"] = company_entity
    return entity_result
