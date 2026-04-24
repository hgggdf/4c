from __future__ import annotations

from typing import Any


TOOL_NAMES = {
    "company_basic_info",
    "financial_metrics",
    "financial_trend",
    "announcement_search",
    "news_search",
    "policy_search",
    "procurement_events",
    "pipeline_search",
    "drug_approval_search",
    "industry_compare",
    "risk_event_search",
    "research_report_search",
    "macro_policy_search",
}


def _text(value: Any) -> str:
    return str(value or "")


def _base_input(
    user_question: str,
    selected_mode: str | None,
    company_entity: dict[str, Any] | None,
    drug_entity: dict[str, Any] | None,
    industry_entity: dict[str, Any] | None,
    time_range: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "user_question": user_question,
        "company_name": (company_entity or {}).get("company_name"),
        "stock_code": (company_entity or {}).get("stock_code"),
        "drug_name": (drug_entity or {}).get("name"),
        "industry_name": (industry_entity or {}).get("name"),
        "time_range": time_range,
        "selected_mode": selected_mode,
    }


def _make_tool(
    tool_name: str,
    *,
    purpose: str,
    required: bool,
    input_payload: dict[str, Any],
    data_source_type: str,
    can_score: bool,
    freshness: str,
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "purpose": purpose,
        "required": required,
        "input": input_payload,
        "data_source_type": data_source_type,
        "can_score": can_score,
        "freshness": freshness,
    }


def _freshness_for(strategy: str | None, hot_default: str = "hot", local_default: str = "local") -> str:
    if strategy == "local_plus_fresh":
        return "fresh"
    if strategy == "local_plus_hot":
        return hot_default
    return local_default


def build_tool_plan(
    user_question: str,
    selected_mode: str | None = None,
    freshness_strategy: str | None = None,
    company_entity: dict[str, Any] | None = None,
    drug_entity: dict[str, Any] | None = None,
    industry_entity: dict[str, Any] | None = None,
    time_range: dict[str, Any] | None = None,
    preference_profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    question = _text(user_question)
    mode = str(selected_mode or "")
    freshness = str(freshness_strategy or "local_only")
    base_input = _base_input(question, selected_mode, company_entity, drug_entity, industry_entity, time_range)
    plan: list[dict[str, Any]] = []

    def add(tool_name: str, *, purpose: str, required: bool, data_source_type: str, can_score: bool, freshness_value: str | None = None) -> None:
        if tool_name not in TOOL_NAMES:
            return
        plan.append(
            _make_tool(
                tool_name,
                purpose=purpose,
                required=required,
                input_payload=dict(base_input),
                data_source_type=data_source_type,
                can_score=can_score,
                freshness=freshness_value or _freshness_for(freshness),
            )
        )

    if mode == "company_analysis":
        add("company_basic_info", purpose="获取公司基础信息", required=True, data_source_type="公司", can_score=False, freshness_value="local")
        add("financial_metrics", purpose="获取公司核心财务指标", required=True, data_source_type="财报", can_score=True, freshness_value="local")
        add("announcement_search", purpose="检索公司公告", required=False, data_source_type="公告", can_score=False, freshness_value="fresh" if freshness == "local_plus_fresh" else "local")
        add("news_search", purpose="检索公司相关新闻", required=False, data_source_type="新闻", can_score=False, freshness_value="fresh" if freshness == "local_plus_fresh" else "local")
        add("research_report_search", purpose="检索相关研报", required=False, data_source_type="研报", can_score=False, freshness_value="local")
        return plan

    if mode == "financial_analysis":
        add("company_basic_info", purpose="获取公司基础信息", required=True, data_source_type="公司", can_score=False, freshness_value="local")
        add("financial_metrics", purpose="获取财务指标", required=True, data_source_type="财报", can_score=True, freshness_value="local")
        add("financial_trend", purpose="获取财务趋势", required=True, data_source_type="财报", can_score=True, freshness_value="local")
        return plan

    if mode == "pipeline_analysis":
        pipeline_input = dict(base_input)
        if drug_entity and drug_entity.get("name"):
            pipeline_input["drug_name"] = drug_entity.get("name")
        plan.append(_make_tool("pipeline_search", purpose="检索药品管线", required=True, input_payload=dict(pipeline_input), data_source_type="药品", can_score=False, freshness=_freshness_for(freshness)))
        plan.append(_make_tool("drug_approval_search", purpose="检索药品获批信息", required=False, input_payload=dict(pipeline_input), data_source_type="药品", can_score=False, freshness=_freshness_for(freshness)))
        plan.append(_make_tool("announcement_search", purpose="检索相关公告", required=False, input_payload=dict(base_input), data_source_type="公告", can_score=False, freshness=_freshness_for(freshness, hot_default="local")))
        plan.append(_make_tool("research_report_search", purpose="检索相关研报", required=False, input_payload=dict(base_input), data_source_type="研报", can_score=False, freshness="local"))
        return plan

    if mode == "policy_procurement":
        add("company_basic_info", purpose="获取公司基础信息", required=True, data_source_type="公司", can_score=False, freshness_value="local")
        add("financial_metrics", purpose="获取财务指标", required=False, data_source_type="财报", can_score=True, freshness_value="local")
        add("procurement_events", purpose="检索集采/采购事件", required=True, data_source_type="政策", can_score=False, freshness_value="fresh" if freshness == "local_plus_fresh" else "hot")
        add("policy_search", purpose="检索政策信息", required=True, data_source_type="政策", can_score=False, freshness_value="fresh" if freshness == "local_plus_fresh" else "hot")
        add("announcement_search", purpose="检索相关公告", required=False, data_source_type="公告", can_score=False, freshness_value="fresh" if freshness == "local_plus_fresh" else "local")
        add("news_search", purpose="检索相关新闻", required=False, data_source_type="新闻", can_score=False, freshness_value="fresh" if freshness == "local_plus_fresh" else "local")
        return plan

    if mode == "risk_warning":
        add("company_basic_info", purpose="获取公司基础信息", required=True, data_source_type="公司", can_score=False, freshness_value="local")
        add("financial_metrics", purpose="获取财务指标", required=False, data_source_type="财报", can_score=True, freshness_value="local")
        add("risk_event_search", purpose="检索风险事件", required=True, data_source_type="新闻", can_score=False, freshness_value="fresh" if freshness == "local_plus_fresh" else "hot")
        add("announcement_search", purpose="检索公告中的风险信息", required=False, data_source_type="公告", can_score=False, freshness_value="fresh" if freshness == "local_plus_fresh" else "local")
        add("news_search", purpose="检索风险相关新闻", required=False, data_source_type="新闻", can_score=False, freshness_value="fresh" if freshness == "local_plus_fresh" else "hot")
        return plan

    if mode == "industry_compare":
        industry_input = dict(base_input)
        if industry_entity and industry_entity.get("name"):
            industry_input["industry_name"] = industry_entity.get("name")
        plan.append(_make_tool("industry_compare", purpose="获取行业对比信息", required=True, input_payload=dict(industry_input), data_source_type="行业", can_score=True, freshness=_freshness_for(freshness, hot_default="local")))
        plan.append(_make_tool("financial_metrics", purpose="获取行业内公司财务指标", required=False, input_payload=dict(industry_input), data_source_type="财报", can_score=True, freshness="local"))
        plan.append(_make_tool("research_report_search", purpose="检索行业研报", required=False, input_payload=dict(industry_input), data_source_type="研报", can_score=False, freshness="local"))
        return plan

    if mode == "chart_analysis":
        if preference_profile and preference_profile.get("content_preferences"):
            content_preferences = preference_profile.get("content_preferences") or []
        else:
            content_preferences = []
        if "risk" in content_preferences:
            add("risk_event_search", purpose="为图表分析补充风险事件数据", required=False, data_source_type="新闻", can_score=False, freshness=_freshness_for(freshness))
        elif "policy_procurement" in content_preferences:
            add("procurement_events", purpose="为图表分析补充政策/集采数据", required=False, data_source_type="政策", can_score=False, freshness=_freshness_for(freshness))
        else:
            add("financial_trend", purpose="为图表分析提供财务趋势数据", required=True, data_source_type="财报", can_score=True, freshness="local")
        return plan

    if mode == "report_generation":
        add("company_basic_info", purpose="获取公司基础信息", required=True, data_source_type="公司", can_score=False, freshness_value="local")
        add("financial_metrics", purpose="获取财务指标", required=True, data_source_type="财报", can_score=True, freshness_value="local")
        add("financial_trend", purpose="获取财务趋势", required=True, data_source_type="财报", can_score=True, freshness_value="local")
        add("announcement_search", purpose="检索公司公告", required=False, data_source_type="公告", can_score=False, freshness_value="local")
        add("news_search", purpose="检索相关新闻", required=False, data_source_type="新闻", can_score=False, freshness_value="local")
        add("research_report_search", purpose="检索研报", required=False, data_source_type="研报", can_score=False, freshness_value="local")
        return plan

    if mode == "quick_query":
        if company_entity:
            add("company_basic_info", purpose="获取公司基础信息", required=False, data_source_type="公司", can_score=False, freshness_value="local")
            add("announcement_search", purpose="检索公告", required=False, data_source_type="公告", can_score=False, freshness_value="local")
            add("news_search", purpose="检索新闻", required=False, data_source_type="新闻", can_score=False, freshness_value="local")
        return plan

    add("company_basic_info", purpose="获取公司基础信息", required=False, data_source_type="公司", can_score=False, freshness_value="local")
    add("announcement_search", purpose="检索公告", required=False, data_source_type="公告", can_score=False, freshness_value="local")
    add("news_search", purpose="检索新闻", required=False, data_source_type="新闻", can_score=False, freshness_value="local")
    return plan
