from __future__ import annotations

from typing import Any


CONTENT_PREFERENCE_ORDER = [
    "financial",
    "pipeline",
    "policy_procurement",
    "risk",
    "industry_compare",
    "news",
]

OUTPUT_PREFERENCE_ORDER = [
    "concise",
    "detailed",
    "chart_first",
    "data_first",
    "evidence_first",
]

CONTENT_MODE_MAP = {
    "financial_analysis": "financial",
    "pipeline_analysis": "pipeline",
    "policy_procurement": "policy_procurement",
    "risk_warning": "risk",
    "industry_compare": "industry_compare",
    "company_analysis": "financial",
    "chart_analysis": "financial",
    "report_generation": "financial",
}

CONTENT_KEYWORDS = {
    "financial": [
        "财务",
        "营收",
        "收入",
        "净利润",
        "利润",
        "毛利率",
        "净利率",
        "现金流",
        "经营现金流",
        "研发费用率",
        "销售费用率",
        "ROE",
        "资产负债率",
        "同比",
        "环比",
    ],
    "pipeline": [
        "管线",
        "药品",
        "新药",
        "临床",
        "临床试验",
        "IND",
        "NDA",
        "BLA",
        "获批",
        "适应症",
        "创新药",
    ],
    "policy_procurement": [
        "集采",
        "带量采购",
        "医保",
        "医保谈判",
        "医保目录",
        "控费",
        "降价",
        "DRG",
        "DIP",
        "政策",
    ],
    "risk": [
        "风险",
        "预警",
        "处罚",
        "监管",
        "负面",
        "暴雷",
        "诉讼",
        "违规",
        "质量问题",
        "召回",
        "问询函",
        "减值",
        "亏损",
        "舆情",
    ],
    "industry_compare": [
        "同行",
        "同业",
        "竞品",
        "竞对",
        "对比",
        "排名",
        "横向比较",
        "相比",
    ],
    "news": [
        "新闻",
        "舆情",
        "最新消息",
        "事件",
        "动态",
        "公告",
    ],
}

OUTPUT_KEYWORDS = {
    "concise": ["简洁", "简单说", "简短", "总结", "一句话", "直接说结论"],
    "detailed": ["详细", "展开", "解释", "分析原因", "讲清楚", "具体说明"],
    "chart_first": ["图表", "画图", "趋势图", "柱状图", "雷达图", "可视化", "用图"],
    "data_first": ["数据", "指标", "数值", "量化", "多少", "比例", "增速"],
    "evidence_first": ["证据", "来源", "引用", "原文", "公告", "财报", "研报", "政策文件"],
}

TIME_LATEST_KEYWORDS = ["最新", "最近", "今天", "今日", "本周", "本月", "近期", "最新消息", "最新公告", "最新政策", "动态"]
TIME_HISTORICAL_KEYWORDS = ["历史", "趋势", "近三年", "近五年", "同比", "环比", "年报", "季报", "过去"]


def _normalize_text(value: Any) -> str:
    return str(value or "")


def _match_keywords(text: str, keywords: list[str]) -> bool:
    lower_text = text.lower()
    for keyword in keywords:
        if keyword.isascii():
            if keyword.lower() in lower_text:
                return True
        elif keyword in text:
            return True
    return False


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def infer_content_preferences(
    user_question: str,
    selected_mode: str | None = None,
    followup_from: str | None = None,
) -> list[str]:
    text = _normalize_text(user_question)
    followup_text = _normalize_text(followup_from)
    result: list[str] = []

    selected_mode_value = _normalize_text(selected_mode).strip() or None
    mapped_mode = CONTENT_MODE_MAP.get(selected_mode_value or "")
    if mapped_mode:
        _append_unique(result, mapped_mode)

    for preference in CONTENT_PREFERENCE_ORDER:
        keywords = CONTENT_KEYWORDS.get(preference, [])
        if _match_keywords(text, keywords) or (followup_text and _match_keywords(followup_text, keywords)):
            _append_unique(result, preference)

    return result


def infer_output_preferences(
    user_question: str,
    preference_hint: dict[str, Any] | None = None,
    followup_from: str | None = None,
) -> list[str]:
    text = _normalize_text(user_question)
    followup_text = _normalize_text(followup_from)
    result: list[str] = []

    hint = preference_hint or {}
    hint_output = hint.get("output")
    if isinstance(hint_output, str) and hint_output in OUTPUT_PREFERENCE_ORDER:
        _append_unique(result, hint_output)
    for key in OUTPUT_PREFERENCE_ORDER:
        if hint.get(key) is True:
            _append_unique(result, key)

    for preference in OUTPUT_PREFERENCE_ORDER:
        keywords = OUTPUT_KEYWORDS.get(preference, [])
        if _match_keywords(text, keywords) or (followup_text and _match_keywords(followup_text, keywords)):
            _append_unique(result, preference)

    return result


def infer_time_preference(
    user_question: str,
    time_range: dict[str, Any] | None = None,
) -> str | None:
    text = _normalize_text(user_question)
    lower_text = text.lower()

    if time_range:
        value = str(time_range.get("value") or "")
        if value in {"today", "recent", "this_week", "this_month", "this_quarter"}:
            return "latest"
        if value.startswith("last_") or value.startswith("year_") or value.startswith("quarter_"):
            return "historical"

    if _match_keywords(text, TIME_LATEST_KEYWORDS):
        return "latest"
    if _match_keywords(text, TIME_HISTORICAL_KEYWORDS):
        return "historical"
    return None


def build_preference_profile(
    user_question: str,
    selected_mode: str | None = None,
    preference_hint: dict[str, Any] | None = None,
    followup_from: str | None = None,
    time_range: dict[str, Any] | None = None,
) -> dict[str, Any]:
    content_preferences = infer_content_preferences(user_question, selected_mode=selected_mode, followup_from=followup_from)
    output_preferences = infer_output_preferences(user_question, preference_hint=preference_hint, followup_from=followup_from)
    time_preference = infer_time_preference(user_question, time_range=time_range)

    sources: list[str] = []
    if selected_mode and infer_content_preferences("", selected_mode=selected_mode):
        _append_unique(sources, "selected_mode")
    if content_preferences or output_preferences or time_preference is not None:
        if _match_keywords(_normalize_text(user_question), sum(CONTENT_KEYWORDS.values(), []) + sum(OUTPUT_KEYWORDS.values(), []) + TIME_LATEST_KEYWORDS + TIME_HISTORICAL_KEYWORDS):
            _append_unique(sources, "user_question")
    if preference_hint and infer_output_preferences("", preference_hint=preference_hint):
        _append_unique(sources, "preference_hint")
    if followup_from and (
        _match_keywords(_normalize_text(followup_from), sum(CONTENT_KEYWORDS.values(), []) + sum(OUTPUT_KEYWORDS.values(), []))
    ):
        _append_unique(sources, "followup_from")
    if time_range and infer_time_preference("", time_range=time_range):
        _append_unique(sources, "time_range")

    source_count = len(sources)
    if source_count == 0:
        confidence = "low"
    elif source_count == 1:
        confidence = "low"
    elif source_count == 2:
        confidence = "medium"
    else:
        confidence = "high"

    return {
        "content_preferences": content_preferences,
        "output_preferences": output_preferences,
        "time_preference": time_preference,
        "sources": sources,
        "confidence": confidence,
    }
