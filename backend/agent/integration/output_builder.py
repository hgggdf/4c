from __future__ import annotations

from typing import Any


def safe_text(value: Any, default: str = "") -> str:
    try:
        if value is None:
            return default
        text = str(value).strip()
        return text if text else default
    except Exception:
        return default


def _has_warning_type(warnings: list[dict[str, Any] | str] | None, warning_type: str) -> bool:
    for item in warnings or []:
        if isinstance(item, dict) and item.get("type") == warning_type:
            return True
    return False


def _company_label(company_entity: dict[str, Any] | None) -> str:
    if not company_entity:
        return "当前标的"
    return safe_text(company_entity.get("company_name")) or safe_text(company_entity.get("stock_name")) or safe_text(company_entity.get("stock_code")) or "当前标的"


def build_summary(
    *,
    selected_mode: str | None = None,
    company_entity: dict[str, Any] | None = None,
    medical_analysis: dict[str, Any] | None = None,
    score_result: dict[str, Any] | None = None,
    warnings: list[dict[str, Any] | str] | None = None,
) -> str | None:
    if _has_warning_type(warnings, "公司未识别"):
        return "当前问题需要明确公司或股票代码，暂无法形成完整结论。"

    status = safe_text((medical_analysis or {}).get("analysis_status"))
    if status == "dry_run_only":
        return "当前已完成分析流程规划，但尚未执行真实数据工具，结论仅作结构化占位。"
    if status == "insufficient":
        return "当前信息不足，暂无法形成完整分析结论。"

    overall_score = (score_result or {}).get("overall_score")
    company_label = _company_label(company_entity)
    if overall_score is not None:
        return f"{company_label} 综合评分为 {overall_score}，建议结合细分维度和证据继续判断。"

    return f"{company_label} 已完成基础分析整理，建议继续补充真实工具数据和证据来源。"


def build_key_points(
    *,
    medical_analysis: dict[str, Any] | None = None,
    key_metrics: list[dict[str, Any]] | None = None,
    evidence_list: list[dict[str, Any]] | None = None,
    warnings: list[dict[str, Any] | str] | None = None,
) -> list[str]:
    if _has_warning_type(warnings, "公司未识别"):
        return [
            "当前问题缺少明确公司或股票代码。",
            "建议补充公司名称或股票代码后重新分析。",
            "系统已保留本轮识别到的其他上下文。",
        ]

    status = safe_text((medical_analysis or {}).get("analysis_status"))
    if status == "dry_run_only":
        return [
            "已完成工具规划和结构化结果占位。",
            "当前尚未执行真实数据工具。",
            "后续需要接入真实工具结果后再形成正式结论。",
        ]

    points: list[str] = []
    for metric in (key_metrics or [])[:3]:
        if not isinstance(metric, dict):
            continue
        name = safe_text(metric.get("name"))
        value = metric.get("value")
        unit = safe_text(metric.get("unit"))
        if not name:
            continue
        value_text = safe_text(value)
        if not value_text:
            continue
        points.append(f"{name}: {value_text}{unit}")

    if evidence_list:
        points.append(f"已整理 {len(evidence_list)} 条证据来源。")

    if not points:
        return [
            "当前结构化信息有限。",
            "建议补充公司、时间范围或分析主题。",
            "后续可结合真实工具数据完善结论。",
        ]

    return points[:5]


def build_answer(
    *,
    summary: str | None = None,
    key_points: list[str] | None = None,
    key_metrics: list[dict[str, Any]] | None = None,
    score_result: dict[str, Any] | None = None,
    chart_payload: list[dict[str, Any]] | None = None,
    evidence_list: list[dict[str, Any]] | None = None,
    warnings: list[dict[str, Any] | str] | None = None,
) -> str:
    lines: list[str] = []
    lines.append(f"一句话结论：{safe_text(summary, '当前信息不足，暂无法形成完整结论。')}")

    if key_points:
        lines.append("关键要点：")
        for item in key_points[:5]:
            lines.append(f"- {safe_text(item)}")

    if key_metrics:
        lines.append("核心指标：")
        for metric in key_metrics[:5]:
            if not isinstance(metric, dict):
                continue
            name = safe_text(metric.get("name"))
            value = safe_text(metric.get("value"))
            unit = safe_text(metric.get("unit"))
            if name and value:
                lines.append(f"- {name}: {value}{unit}")

    if score_result and score_result.get("overall_score") is not None:
        lines.append("评分：")
        lines.append(f"- 综合评分 {safe_text(score_result.get('overall_score'))}")
        level = safe_text(score_result.get("level"))
        if level:
            lines.append(f"- 评级 {level}")

    if chart_payload:
        lines.append("图表：")
        for chart in chart_payload[:3]:
            if not isinstance(chart, dict):
                continue
            title = safe_text(chart.get("title"), "图表")
            chart_type = safe_text(chart.get("chart_type"), "chart")
            lines.append(f"- {title}（{chart_type}）")

    if evidence_list:
        evidence_is_placeholder = any(
            isinstance(item, dict) and "dry_run" in safe_text(item.get("summary"))
            for item in evidence_list
        )
        if evidence_is_placeholder:
            lines.append("证据：当前仅为 dry_run 占位证据，尚未接入真实来源。")
        else:
            lines.append(f"证据：已整理 {len(evidence_list)} 条来源。")

    warning_texts: list[str] = []
    for item in warnings or []:
        if isinstance(item, dict):
            warning_texts.append(f"{safe_text(item.get('type'))}: {safe_text(item.get('message'))}")
        else:
            warning_texts.append(safe_text(item))
    if warning_texts:
        lines.append("注意事项：")
        for item in warning_texts[:5]:
            lines.append(f"- {item}")

    answer = "\n".join(line for line in lines if line.strip())
    return answer.strip() or "当前信息不足，暂无法形成完整结论。"


def build_industry_compare_answer(tool_results: list[dict[str, Any]] | None) -> str | None:
    """从 industry_compare 工具结果构建并排对比文本。"""
    for item in tool_results or []:
        if not isinstance(item, dict):
            continue
        if item.get("tool_name") != "industry_compare" or not item.get("success"):
            continue
        data = item.get("data") or {}
        if data.get("dry_run"):
            return None
        companies = data.get("companies") or {}
        comparison = data.get("comparison") or {}
        stock_codes = data.get("stock_codes") or []
        if not companies or not comparison or len(stock_codes) < 2:
            return None

        METRIC_LABELS = {
            "gross_margin": "毛利率(%)",
            "net_margin": "净利率(%)",
            "roe": "ROE(%)",
            "rd_ratio": "研发费用率(%)",
            "revenue_growth": "营收增速(%)",
        }

        # 表头
        names = [safe_text((companies.get(c) or {}).get("stock_name") or c) for c in stock_codes]
        header = "| 指标 | " + " | ".join(names) + " |"
        sep = "|------|" + "------|" * len(stock_codes)
        rows = [header, sep]

        for metric, label in METRIC_LABELS.items():
            metric_data = comparison.get(metric)
            if not metric_data:
                continue
            cells = []
            for code in stock_codes:
                values = metric_data.get(code) or []
                if values:
                    latest = values[0]
                    v = latest.get("value")
                    cells.append(f"{v:.2f}" if isinstance(v, (int, float)) else str(v or "--"))
                else:
                    cells.append("--")
            rows.append(f"| {label} | " + " | ".join(cells) + " |")

        return "行业对比（最新期）：\n\n" + "\n".join(rows)
    return None


def build_structured_output(
    *,
    selected_mode: str | None = None,
    company_entity: dict[str, Any] | None = None,
    medical_analysis: dict[str, Any] | None = None,
    score_result: dict[str, Any] | None = None,
    key_metrics: list[dict[str, Any]] | None = None,
    chart_payload: list[dict[str, Any]] | None = None,
    evidence_list: list[dict[str, Any]] | None = None,
    warnings: list[dict[str, Any] | str] | None = None,
    tool_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    # 行业对比模式：优先用对比表格作为 answer
    if selected_mode == "industry_compare":
        compare_answer = build_industry_compare_answer(tool_results)
        if compare_answer:
            return {
                "summary": "已完成行业对比分析。",
                "key_points": [],
                "answer": compare_answer,
            }

    summary = build_summary(
        selected_mode=selected_mode,
        company_entity=company_entity,
        medical_analysis=medical_analysis,
        score_result=score_result,
        warnings=warnings,
    )
    key_points = build_key_points(
        medical_analysis=medical_analysis,
        key_metrics=key_metrics,
        evidence_list=evidence_list,
        warnings=warnings,
    )
    answer = build_answer(
        summary=summary,
        key_points=key_points,
        key_metrics=key_metrics,
        score_result=score_result,
        chart_payload=chart_payload,
        evidence_list=evidence_list,
        warnings=warnings,
    )
    return {
        "summary": summary,
        "key_points": key_points,
        "answer": answer,
    }
