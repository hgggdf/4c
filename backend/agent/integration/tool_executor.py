from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from agent.tools import announcement_tools, company_tools, financial_tools, macro_tools, news_tools, retrieval_tools


def safe_to_dict(value: Any) -> Any:
    try:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if is_dataclass(value):
            return safe_to_dict(asdict(value))
        if isinstance(value, list):
            return [safe_to_dict(item) for item in value]
        if isinstance(value, dict):
            return {str(key): safe_to_dict(item) for key, item in value.items()}
        if hasattr(value, "model_dump"):
            try:
                return safe_to_dict(value.model_dump())
            except Exception:
                pass
        if hasattr(value, "dict"):
            try:
                return safe_to_dict(value.dict())
            except Exception:
                pass
        return {"repr": str(value)}
    except Exception:
        try:
            return {"repr": str(value)}
        except Exception:
            return {"repr": "<unserializable>"}


def normalize_tool_result(
    tool_name: str,
    *,
    success: bool,
    data: Any = None,
    evidence_sources: list[dict[str, Any]] | None = None,
    updated_at: str | None = None,
    data_source_type: str | None = None,
    warning: str | None = None,
    error: str | None = None,
    can_score: bool = False,
    freshness: str | None = None,
) -> dict[str, Any]:
    normalized_data = safe_to_dict(data)
    normalized_sources = safe_to_dict(evidence_sources or [])
    if not isinstance(normalized_sources, list):
        normalized_sources = []
    return {
        "tool_name": tool_name,
        "success": success,
        "data": normalized_data,
        "evidence_sources": normalized_sources,
        "updated_at": updated_at,
        "data_source_type": data_source_type,
        "warning": warning,
        "error": error,
        "can_score": can_score,
        "freshness": freshness,
    }


def _planned_input(plan_item: dict[str, Any]) -> dict[str, Any]:
    raw = plan_item.get("input") or {}
    return raw if isinstance(raw, dict) else {}


def _run_tool(tool_name: str, input_data: dict[str, Any]) -> tuple[bool, Any, str | None]:
    stock_code = input_data.get("stock_code")
    company_name = input_data.get("company_name")
    user_question = input_data.get("user_question")
    industry_name = input_data.get("industry_name")

    if tool_name == "company_basic_info":
        if not stock_code:
            return False, None, "缺少必需参数 stock_code"
        return True, company_tools.get_company_basic_info(stock_code), None

    if tool_name == "financial_metrics":
        if not stock_code:
            return False, None, "缺少必需参数 stock_code"
        return True, financial_tools.get_financial_metrics(stock_code, ["gross_margin", "net_margin", "roe", "rd_ratio"]), None

    if tool_name == "announcement_search":
        if not stock_code:
            return False, None, "缺少必需参数 stock_code"
        return True, announcement_tools.get_structured_announcements(stock_code), None

    if tool_name == "news_search":
        if stock_code:
            return True, news_tools.get_news_by_company(stock_code), None
        if company_name:
            return True, news_tools.get_news_by_company(company_name), None
        return False, None, "缺少必需参数 stock_code 或 company_name"

    if tool_name == "procurement_events":
        if not stock_code:
            return False, None, "缺少必需参数 stock_code"
        return True, announcement_tools.get_procurement_events(stock_code), None

    if tool_name == "risk_event_search":
        if not stock_code:
            return False, None, "缺少必需参数 stock_code"
        return True, announcement_tools.get_regulatory_risks(stock_code), None

    if tool_name == "drug_approval_search":
        if not stock_code:
            return False, None, "缺少必需参数 stock_code"
        return True, announcement_tools.get_drug_approvals(stock_code), None

    if tool_name == "pipeline_search":
        if not stock_code:
            return False, None, "缺少必需参数 stock_code"
        return True, announcement_tools.get_clinical_trials(stock_code), None

    if tool_name == "research_report_search":
        if not user_question:
            return False, None, "缺少必需参数 user_question"
        return True, retrieval_tools.search_company_evidence(str(user_question), stock_code=stock_code), None

    if tool_name == "macro_policy_search":
        if not user_question and not industry_name:
            return False, None, "缺少必需参数 user_question 或 industry_name"
        query = str(user_question or industry_name or "")
        return True, macro_tools.get_macro_summary([query]), None

    return False, None, "未配置真实工具映射"


def execute_tool_plan(
    tool_plan: list[dict[str, Any]],
    *,
    dry_run: bool = True,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for plan_item in tool_plan or []:
        tool_name = str(plan_item.get("tool_name") or "")
        input_data = _planned_input(plan_item)
        data_source_type = plan_item.get("data_source_type")
        can_score = bool(plan_item.get("can_score", False))
        freshness = plan_item.get("freshness")

        if dry_run:
            results.append(
                normalize_tool_result(
                    tool_name,
                    success=True,
                    data={
                        "dry_run": True,
                        "planned_input": safe_to_dict(input_data),
                        "message": "工具计划已生成，未执行真实工具",
                    },
                    evidence_sources=[],
                    updated_at=None,
                    data_source_type=data_source_type,
                    warning="dry_run 模式未执行真实工具",
                    error=None,
                    can_score=can_score,
                    freshness=freshness,
                )
            )
            continue

        try:
            success, data, error = _run_tool(tool_name, input_data)
            results.append(
                normalize_tool_result(
                    tool_name,
                    success=success,
                    data=data if success else None,
                    evidence_sources=[],
                    updated_at=None,
                    data_source_type=data_source_type,
                    warning=None if success else error,
                    error=None if success else error,
                    can_score=can_score,
                    freshness=freshness,
                )
            )
        except Exception as exc:
            results.append(
                normalize_tool_result(
                    tool_name,
                    success=False,
                    data=None,
                    evidence_sources=[],
                    updated_at=None,
                    data_source_type=data_source_type,
                    warning=str(exc),
                    error=str(exc),
                    can_score=can_score,
                    freshness=freshness,
                )
            )
    return results
