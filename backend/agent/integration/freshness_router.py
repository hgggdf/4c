from __future__ import annotations

from typing import Any


LATEST_KEYWORDS = [
    "最新",
    "最近",
    "今日",
    "今天",
    "本周",
    "本月",
    "近期",
    "最新公告",
    "最新新闻",
    "最新政策",
    "最新消息",
    "动态",
    "刚刚",
    "现在",
]

HISTORICAL_KEYWORDS = [
    "近三年",
    "近五年",
    "历史",
    "趋势",
    "年报",
    "季报",
    "同比",
    "环比",
    "过去",
]

POLICY_KEYWORDS = [
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
]

RISK_KEYWORDS = [
    "风险",
    "预警",
    "处罚",
    "监管",
    "负面",
    "暴雷",
    "问询函",
    "召回",
    "舆情",
]

LATEST_TIME_VALUES = {"today", "recent", "this_week", "this_month", "this_quarter"}
HISTORICAL_TIME_PREFIXES = ("last_", "year_", "quarter_")


def _text(value: Any) -> str:
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


def has_latest_intent(
    user_question: str,
    time_range: dict[str, Any] | None = None,
    preference_profile: dict[str, Any] | None = None,
) -> bool:
    text = _text(user_question)
    if _match_keywords(text, LATEST_KEYWORDS):
        return True

    if time_range and str(time_range.get("value") or "") in LATEST_TIME_VALUES:
        return True

    if preference_profile and str(preference_profile.get("time_preference") or "") == "latest":
        return True

    return False


def has_historical_intent(
    user_question: str,
    time_range: dict[str, Any] | None = None,
    preference_profile: dict[str, Any] | None = None,
) -> bool:
    text = _text(user_question)
    if _match_keywords(text, HISTORICAL_KEYWORDS):
        return True

    if time_range:
        value = str(time_range.get("value") or "")
        if value.startswith(HISTORICAL_TIME_PREFIXES):
            return True

    if preference_profile and str(preference_profile.get("time_preference") or "") == "historical":
        return True

    return False


def requires_company_entity(selected_mode: str | None) -> bool:
    return str(selected_mode or "") in {
        "company_analysis",
        "financial_analysis",
        "policy_procurement",
        "risk_warning",
        "chart_analysis",
        "report_generation",
    }


def determine_freshness_strategy(
    user_question: str,
    selected_mode: str | None = None,
    company_entity: dict[str, Any] | None = None,
    drug_entity: dict[str, Any] | None = None,
    industry_entity: dict[str, Any] | None = None,
    time_range: dict[str, Any] | None = None,
    preference_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    question = _text(user_question)
    mode = str(selected_mode or "")

    if requires_company_entity(mode) and not company_entity:
        return {
            "strategy": "insufficient",
            "reason": "当前模式需要公司实体，但未识别到公司或股票代码",
            "warnings": [
                {
                    "type": "公司未识别",
                    "message": "当前问题需要公司或股票代码，但未识别到明确公司实体",
                    "detail": {"selected_mode": selected_mode},
                }
            ],
        }

    latest_intent = has_latest_intent(question, time_range=time_range, preference_profile=preference_profile)
    historical_intent = has_historical_intent(question, time_range=time_range, preference_profile=preference_profile)

    if latest_intent:
        return {"strategy": "local_plus_fresh", "reason": "检测到最新数据意图", "warnings": []}

    if mode == "policy_procurement" or _match_keywords(question, POLICY_KEYWORDS):
        return {"strategy": "local_plus_hot", "reason": "政策/集采/医保相关问题通常依赖热点数据", "warnings": []}

    if mode == "risk_warning" or _match_keywords(question, RISK_KEYWORDS):
        return {"strategy": "local_plus_hot", "reason": "风险预警问题通常依赖热点数据", "warnings": []}

    if mode == "financial_analysis" and historical_intent:
        return {"strategy": "local_only", "reason": "历史财务趋势优先使用本地数据", "warnings": []}

    if mode == "pipeline_analysis":
        return {
            "strategy": "local_plus_fresh" if latest_intent else "local_plus_hot",
            "reason": "药品管线问题优先结合最新或热点数据",
            "warnings": [],
        }

    if mode == "industry_compare":
        return {
            "strategy": "local_plus_fresh" if latest_intent else "local_only",
            "reason": "行业对比问题根据时效性决定是否需要新数据",
            "warnings": [],
        }

    return {"strategy": "local_only", "reason": "默认使用本地数据", "warnings": []}
