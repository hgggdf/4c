# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any
from .entity_resolver import extract_company_name, extract_stock_code, has_reference_pronoun, resolve_entities

_COMPANY_REQUIRED_MODES = {"company_analysis","financial_analysis","pipeline_analysis","risk_warning","attribution_analysis","report_generation"}
_NO_CLARIFY_MODES = {"policy_procurement","industry_compare","chart_analysis","quick_query"}
_SHORT_QUESTION_THRESHOLD = 6
_VAGUE_KEYWORDS = ["分析一下","帮我看看","怎么样","如何","说说","讲讲","介绍"]

def _is_vague_without_subject(question):
    q = str(question or "")
    has_vague = any(kw in q for kw in _VAGUE_KEYWORDS)
    has_company = bool(extract_stock_code(q) or extract_company_name(q))
    return has_vague and not has_company

def detect_clarification(user_question, *, selected_mode=None, history=None, targets=None, current_stock_code=None):
    q = str(user_question or "").strip()
    mode = str(selected_mode or "")
    if mode in _NO_CLARIFY_MODES:
        return _no_clarification()
    if len(q) <= _SHORT_QUESTION_THRESHOLD and not extract_stock_code(q) and not extract_company_name(q):
        return _make_clarification(
            reason="问题过短",
            question="您想分析哪家公司或哪个行业？",
            suggestions=["恒瑞医药","药明康德","医保政策影响"],
        )
    entity_result = resolve_entities(q, history=history, targets=targets, current_stock_code=current_stock_code)
    company_entity = entity_result.get("company_entity")
    has_reference = has_reference_pronoun(q)
    if has_reference and not company_entity:
        return _make_clarification(
            reason="指代不明确",
            question="您说的“这家公司”是指哪家？请告诉我公司名称或股票代码。",
            suggestions=["恒瑞医药(600276)","药明康德(603259)","迈瑞医疗(300760)"],
        )
    if mode in _COMPANY_REQUIRED_MODES and not company_entity and not targets:
        return _make_clarification(
            reason="缺少分析主体",
            question="请问您想对哪家公司进行" + _mode_label(mode) + "？",
            suggestions=["恒瑞医药","百济神州","迈瑞医疗"],
        )
    if _is_vague_without_subject(q) and not company_entity and not targets:
        return _make_clarification(
            reason="问题主体不明确",
            question="您想分析哪家公司？可以直接输入公司名称或股票代码。",
            suggestions=["恒瑞医药","药明康德","百济神州"],
        )
    return _no_clarification()

def _mode_label(mode):
    labels = {"company_analysis":"综合分析","financial_analysis":"财务分析","pipeline_analysis":"管线分析","risk_warning":"风险预警","attribution_analysis":"归因分析","report_generation":"报告生成"}
    return labels.get(mode, "分析")

def _make_clarification(*, reason, question, suggestions):
    return {"need_clarification": True, "reason": reason, "question": question, "suggestions": suggestions[:3]}

def _no_clarification():
    return {"need_clarification": False, "reason": "", "question": "", "suggestions": []}

__all__ = ["detect_clarification"]
