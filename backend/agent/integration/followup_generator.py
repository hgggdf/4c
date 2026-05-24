from __future__ import annotations

from typing import Any


def _safe_text(value: Any, default: str = "") -> str:
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


def _company_name(company_entity: dict[str, Any] | None) -> str:
    if not company_entity:
        return "该公司"
    return _safe_text(company_entity.get("company_name")) or _safe_text(company_entity.get("stock_name")) or "该公司"


def _industry_name(industry_entity: dict[str, Any] | None) -> str:
    if not industry_entity:
        return "该行业"
    return _safe_text(industry_entity.get("name")) or "该行业"


def _default_questions() -> list[str]:
    return [
        "需要进一步分析财务表现吗？",
        "需要补充风险和政策影响吗？",
        "要不要和同行做对比？",
    ]


def generate_follow_up_questions(
    *,
    user_question: str,
    selected_mode: str | None = None,
    company_entity: dict[str, Any] | None = None,
    drug_entity: dict[str, Any] | None = None,
    industry_entity: dict[str, Any] | None = None,
    warnings: list[dict[str, Any] | str] | None = None,
) -> list[str]:
    default_questions = _default_questions()
    if _has_warning_type(warnings, "公司未识别"):
        return [
            "要分析哪家公司？",
            "可以补充股票代码吗？",
            "需要我先按行业维度分析吗？",
        ]

    mode = _safe_text(selected_mode)
    company_name = _company_name(company_entity)
    industry_name = _industry_name(industry_entity)

    if mode == "policy_procurement":
        questions = [
            f"{company_name}哪些产品受集采影响最大？",
            "集采会压缩多少利润空间？",
            "和同行相比政策风险高吗？",
        ]
    elif mode == "financial_analysis":
        questions = [
            f"{company_name}近三年营收趋势如何？",
            "毛利率和净利率变化是否健康？",
            "和同行相比财务质量强吗？",
        ]
    elif mode == "pipeline_analysis":
        questions = [
            f"{company_name}核心管线进展如何？",
            "哪些药品最接近商业化？",
            "管线失败风险主要在哪里？",
        ]
    elif mode == "risk_warning":
        questions = [
            f"{company_name}近期有哪些主要风险？",
            "风险会影响利润还是估值？",
            "同行是否也面临类似风险？",
        ]
    elif mode == "industry_compare":
        questions = [
            f"{industry_name}里谁的增长更快？",
            "这个行业主要风险是什么？",
            "哪些公司更值得横向对比？",
        ]
    elif mode == "chart_analysis":
        questions = [
            "要看哪项指标的趋势图？",
            "需要和同行做柱状对比吗？",
            "是否生成风险雷达图？",
        ]
    elif mode == "report_generation":
        questions = [
            "要生成简版还是详细版报告？",
            "报告需要加入图表吗？",
            "是否加入证据来源列表？",
        ]
    else:
        questions = default_questions[:]

    if len(questions) < 3:
        questions.extend(default_questions)
    deduped: list[str] = []
    for question in questions:
        q = _safe_text(question)
        if not q:
            continue
        if _safe_text(user_question) and q == _safe_text(user_question):
            q = default_questions[len(deduped) % len(default_questions)]
        if q not in deduped:
            deduped.append(q)
        if len(deduped) == 3:
            break

    for fallback in default_questions:
        if len(deduped) == 3:
            break
        if fallback not in deduped:
            deduped.append(fallback)

    return deduped[:3]
