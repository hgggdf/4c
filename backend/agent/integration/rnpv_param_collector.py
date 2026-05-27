"""
rNPV dialogue parameter collector.

Parses already-confirmed parameters from conversation history and decides
which field to ask next.  Collection order:
  indication -> trial_phase -> target_patients_wan -> price_per_year_wan -> peak_market_share

Returns None for next_field when all fields are present (ready to calculate).
"""
from __future__ import annotations

import re
from typing import Any

_FIELDS_IN_ORDER = [
    "indication",
    "trial_phase",
    "target_patients_wan",
    "price_per_year_wan",
    "peak_market_share",
]

_QUESTION_MAP: dict[str, dict] = {
    "indication": {
        "question": "请问该药品的主要适应症是什么？（例如：非小细胞肺癌、2型糖尿病）",
        "suggestions": ["非小细胞肺癌", "乙型肝炎", "2型糖尿病"],
    },
    "trial_phase": {
        "question": "该药品目前处于哪个临床阶段？",
        "suggestions": ["Phase I（一期）", "Phase II（二期）", "Phase III（三期）", "NDA申报"],
    },
    "target_patients_wan": {
        "question": "预计目标患者群体有多大？（万人，如 50 表示 50 万人；不确定请回复【不知道】使用行业基准）",
        "suggestions": ["50万人", "100万人", "200万人", "不知道，用行业基准"],
    },
    "price_per_year_wan": {
        "question": "预计年治疗费用大约多少？（万元/人/年，如 5 表示 5 万元；不确定请回复【不知道】）",
        "suggestions": ["1万元/年", "5万元/年", "20万元/年", "不知道，用行业基准"],
    },
    "peak_market_share": {
        "question": "预计峰值市场份额大概多少？（如 15% 或 0.15；不确定请回复【不知道】）",
        "suggestions": ["5%", "15%", "30%", "不知道，用行业基准"],
    },
}

_PHASE_PATTERNS = [
    (re.compile(r"(iii|三期|phase\s*3|3期)", re.I), "phase3"),
    (re.compile(r"phase\s*2[_\-]?3|二三期", re.I), "phase2_3"),
    (re.compile(r"(ii|二期|phase\s*2|2期)", re.I), "phase2"),
    (re.compile(r"(i期|一期|phase\s*1|1期)", re.I), "phase1"),
    (re.compile(r"(nda|申报|上市申请|bla)", re.I), "nda"),
    (re.compile(r"(已上市|approved)", re.I), "approved"),
]

_DONT_KNOW = re.compile(
    r"不知道|不清楚|不确定|没有数据|用基准|行业基准|跳过|default|skip|not\s+sure|unknown",
    re.I,
)


def _parse_phase(text: str) -> str | None:
    for pattern, value in _PHASE_PATTERNS:
        if pattern.search(text):
            return value
    return None


def _parse_float(text: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if m:
        return float(m.group(1)) / 100
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    if m:
        return float(m.group(1))
    return None


def _extract_from_message(field: str, text: str) -> Any:
    """Try to extract a field value from one user message.

    Returns:
        False  — user explicitly said they don't know (use fallback)
        None   — could not parse anything useful
        value  — parsed value
    """
    if _DONT_KNOW.search(text):
        return False

    if field == "indication":
        cleaned = re.sub(
            r"^(适应症[是为：:]\s*|主要[是为：:]\s*|针对\s*|indication\s*[：:=]\s*)",
            "",
            text.strip(),
            flags=re.I,
        )
        # 纯数字或极短数字串不是适应症
        if re.fullmatch(r"[\d\s.,/%-]+", cleaned):
            return None
        if 2 <= len(cleaned) <= 40:
            return cleaned
        return None

    if field == "trial_phase":
        # 纯数字不当作阶段名解析（避免 "50" 被 "1期" 正则误匹配）
        if re.fullmatch(r"\d+(?:\.\d+)?", text.strip()):
            return None
        return _parse_phase(text)

    if field == "target_patients_wan":
        val = _parse_float(text)
        if val is not None and 0.1 <= val <= 50000:
            return val
        return None

    if field == "price_per_year_wan":
        val = _parse_float(text)
        if val is not None and 0.01 <= val <= 10000:
            return val
        return None

    if field == "peak_market_share":
        val = _parse_float(text)
        if val is not None:
            if val > 1:
                val = val / 100
            if 0 < val <= 1:
                return val
        return None

    return None


def collect_rnpv_params(
    history: list[dict[str, str]] | None,
    *,
    prefill: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str | None]:
    """Scan history and prefill to build the parameter dict collected so far.

    prefill values (from pipeline_drugs table) are treated as defaults and
    can be overridden by explicit user messages.

    Returns:
        (params, next_field)
        next_field is None when all fields are present — ready to calculate.
        A field value of None means the user said they don't know; the
        calculator will use its industry-benchmark fallback.
    """
    params: dict[str, Any] = {}

    for field in _FIELDS_IN_ORDER:
        v = (prefill or {}).get(field)
        if v is not None:
            params[field] = v

    for msg in (history or []):
        if msg.get("role") != "user":
            continue
        text = str(msg.get("content") or "").strip()
        if not text:
            continue
        # Find the first field that still needs to be collected and try to
        # parse it from this message.  Only one field per user turn — this
        # prevents a single numeric reply from filling multiple fields at once.
        for field in _FIELDS_IN_ORDER:
            if field in params:
                continue
            val = _extract_from_message(field, text)
            if val is not None:
                params[field] = None if val is False else val
            # Whether we got a value or not, stop here so we don't consume
            # later fields from the same message.
            break

    for field in _FIELDS_IN_ORDER:
        if field not in params:
            return params, field

    return params, None


def get_next_question(field: str) -> dict:
    """Return the question text and chip suggestions for the given field."""
    return _QUESTION_MAP[field]
