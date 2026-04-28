from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


KEY_METRIC_NAMES = [
    "营收",
    "净利润",
    "毛利率",
    "净利率",
    "ROE",
    "研发费用率",
    "销售费用率",
    "资产负债率",
    "现金流",
]


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


def extract_successful_tool_data(tool_results: list[dict[str, Any]] | None) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in tool_results or []:
        if not isinstance(item, dict) or item.get("success") is not True:
            continue
        tool_name = str(item.get("tool_name") or "")
        if not tool_name:
            continue
        grouped.setdefault(tool_name, []).append(safe_to_dict(item.get("data")))
    return grouped


def _first_available(tool_data: dict[str, list[dict[str, Any]]], names: list[str]) -> list[dict[str, Any]]:
    for name in names:
        data = tool_data.get(name)
        if data:
            return data
    return []


def build_key_metrics(tool_data: dict[str, list[dict[str, Any]]], company_entity: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    company_name = (company_entity or {}).get("company_name")
    stock_code = (company_entity or {}).get("stock_code")

    if company_name:
        metrics.append({"name": "公司", "value": company_name, "unit": "", "source": "company_entity", "confidence": "high"})
    if stock_code:
        metrics.append({"name": "股票代码", "value": stock_code, "unit": "", "source": "company_entity", "confidence": "high"})

    financial_items = _first_available(tool_data, ["financial_metrics", "financial_summary"])
    for item in financial_items:
        if not isinstance(item, dict):
            continue
        for key, display in [
            ("revenue", "营收"),
            ("net_profit", "净利润"),
            ("gross_margin", "毛利率"),
            ("net_margin", "净利率"),
            ("roe", "ROE"),
            ("rd_ratio", "研发费用率"),
            ("selling_ratio", "销售费用率"),
            ("debt_ratio", "资产负债率"),
            ("operating_cashflow", "现金流"),
            ("cashflow_quality", "现金流"),
        ]:
            value = item.get(key)
            if value is None:
                continue
            metrics.append({
                "name": display,
                "value": value,
                "unit": item.get("metric_unit") or item.get("unit") or "",
                "source": "financial_metrics",
                "confidence": "medium",
            })
    return metrics


def build_evidence_list(tool_results: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for item in tool_results or []:
        if not isinstance(item, dict) or item.get("success") is not True:
            continue
        tool_name = str(item.get("tool_name") or "")
        data_source_type = str(item.get("data_source_type") or "") or None
        updated_at = item.get("updated_at")
        data = safe_to_dict(item.get("data"))
        dry_run = bool(isinstance(data, dict) and data.get("dry_run") is True)
        evidence_sources = item.get("evidence_sources") or []
        if evidence_sources:
            for source in evidence_sources:
                src = safe_to_dict(source)
                if not isinstance(src, dict):
                    continue
                evidence.append({
                    "source_type": src.get("source_type") or data_source_type,
                    "title": src.get("title") or tool_name,
                    "summary": src.get("summary") or ("dry_run 模式下未执行真实工具，仅生成计划占位" if dry_run else "工具结果已生成"),
                    "url": src.get("url"),
                    "publish_date": src.get("publish_date") or updated_at,
                    "tool_name": tool_name,
                })
        else:
            evidence.append({
                "source_type": data_source_type,
                "title": tool_name,
                "summary": "dry_run 模式下未执行真实工具，仅生成计划占位" if dry_run else "工具结果已生成",
                "url": None,
                "publish_date": updated_at,
                "tool_name": tool_name,
            })
        if len(evidence) >= 10:
            break
    return evidence[:10]


def build_score_result(
    tool_data: dict[str, list[dict[str, Any]]],
    selected_mode: str | None = None,
) -> dict[str, Any] | None:
    for key in ("score_result", "scoring", "pharma_score_result"):
        items = tool_data.get(key)
        if not items:
            continue
        first = items[0]
        if not isinstance(first, dict):
            continue
        if first.get("dry_run") is True:
            return None
        dimensions = safe_to_dict(first.get("dimensions")) or []
        if not dimensions:
            return None
        return {
            "overall_score": first.get("overall_score") or first.get("total_score"),
            "dimensions": dimensions if isinstance(dimensions, list) else [],
            "level": first.get("level"),
            "source": "tool_results",
        }
    return None


def build_chart_payload(
    tool_data: dict[str, list[dict[str, Any]]],
    score_result: dict[str, Any] | None = None,
    preference_profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    charts: list[dict[str, Any]] = []
    if score_result and isinstance(score_result.get("dimensions"), list) and score_result.get("dimensions"):
        charts.append({
            "chart_type": "radar",
            "title": "综合评分雷达图",
            "data": safe_to_dict(score_result.get("dimensions")),
            "source": "score_result",
        })

    trend_items = tool_data.get("financial_trend") or []
    for item in trend_items:
        if not isinstance(item, dict):
            continue
        points = item.get("points") or item.get("trend") or []
        if points:
            charts.append({
                "chart_type": "line",
                "title": str(item.get("metric") or "财务趋势"),
                "data": safe_to_dict(points),
                "source": "financial_trend",
            })
            break

    if charts:
        return charts
    if preference_profile and "chart_first" in (preference_profile.get("output_preferences") or []):
        return []
    return []


def _analysis_status(tool_plan: list[dict[str, Any]] | None, tool_results: list[dict[str, Any]] | None, dry_run: bool) -> str:
    if not tool_plan:
        return "insufficient"
    if not tool_results:
        return "partial"
    if dry_run:
        return "dry_run_only"
    if any(item.get("success") for item in tool_results or []):
        return "ready"
    return "partial"


def build_medical_analysis(
    *,
    user_question: str,
    selected_mode: str | None = None,
    company_entity: dict[str, Any] | None = None,
    drug_entity: dict[str, Any] | None = None,
    industry_entity: dict[str, Any] | None = None,
    time_range: dict[str, Any] | None = None,
    preference_profile: dict[str, Any] | None = None,
    freshness_strategy: str | None = None,
    tool_plan: list[dict[str, Any]] | None = None,
    tool_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    tool_data = extract_successful_tool_data(tool_results)
    dry_run_flags = [bool(isinstance(safe_to_dict(item.get("data")), dict) and safe_to_dict(item.get("data")).get("dry_run") is True) for item in (tool_results or []) if isinstance(item, dict) and item.get("success") is True]
    all_or_majority_dry_run = bool(dry_run_flags) and sum(1 for flag in dry_run_flags if flag) >= max(1, len(dry_run_flags) // 2)
    status = _analysis_status(tool_plan, tool_results, all_or_majority_dry_run)

    medical_analysis: dict[str, Any] | None
    if not tool_plan:
        medical_analysis = {
            "mode": selected_mode,
            "company": company_entity,
            "drug": drug_entity,
            "industry": industry_entity,
            "time_range": time_range,
            "freshness_strategy": freshness_strategy,
            "tool_count": 0,
            "successful_tool_count": 0,
            "dry_run": False,
            "analysis_status": "insufficient",
            "summary": "尚未生成工具计划",
        }
    else:
        successful_tool_count = sum(1 for item in tool_results or [] if isinstance(item, dict) and item.get("success") is True)
        medical_analysis = {
            "mode": selected_mode,
            "company": safe_to_dict(company_entity),
            "drug": safe_to_dict(drug_entity),
            "industry": safe_to_dict(industry_entity),
            "time_range": safe_to_dict(time_range),
            "freshness_strategy": freshness_strategy,
            "tool_count": len(tool_plan or []),
            "successful_tool_count": successful_tool_count,
            "dry_run": all_or_majority_dry_run,
            "analysis_status": status,
            "summary": f"{selected_mode or 'quick_query'} 分析已完成基础适配，当前状态为 {status}",
        }

    score_result = build_score_result(tool_data, selected_mode=selected_mode)
    key_metrics = build_key_metrics(tool_data, company_entity=company_entity)
    evidence_list = build_evidence_list(tool_results)
    chart_payload = build_chart_payload(tool_data, score_result=score_result, preference_profile=preference_profile)

    warnings: list[dict[str, Any] | str] = []
    if status == "dry_run_only":
        warnings.append({
            "type": "工具未真实执行",
            "message": "当前仅完成工具规划与占位结果，尚未执行真实数据工具",
            "detail": {},
        })
    for item in tool_results or []:
        if not isinstance(item, dict) or item.get("success") is not False:
            continue
        warnings.append({
            "type": "工具结果失败",
            "message": str(item.get("error") or item.get("warning") or "工具结果失败"),
            "detail": {"tool_name": item.get("tool_name")},
        })

    return {
        "medical_analysis": medical_analysis,
        "score_result": score_result,
        "key_metrics": key_metrics,
        "chart_payload": chart_payload,
        "evidence_list": evidence_list,
        "warnings": warnings,
    }
