from __future__ import annotations

import json
import re
from typing import Any


def _compact_text(value: Any, *, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _serialize_history(history: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for item in (history or [])[-4:]:
        role = str(item.get("role") or "user").strip() or "user"
        content = _compact_text(item.get("content") or "", limit=120)
        if content:
            items.append({"role": role, "content": content})
    return items


def build_chat_messages(
    *,
    user_question: str,
    stock_context: dict[str, Any] | None,
    analysis_summary: dict[str, Any] | None,
    chart_context: list[dict[str, Any]] | None,
    evidence_items: list[dict[str, Any]],
    history: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    history_payload = _serialize_history(history)
    system_content = (
        "你是医药企业分析系统中的最小总结层。"
        "只允许基于输入里的 stock_context、analysis_summary、chart_context、history、evidence_items 作答。"
        "禁止编造数据库结果、指标值、公告内容或公司代码。"
        "你必须只输出一个可直接被 json.loads 解析的 JSON 对象。"
        "不要输出任何解释、前后缀、补充说明、思考过程，也不要输出 markdown 代码块。"
        "输出对象字段固定且只能包含 answer、suggestion、chart_desc、report_markdown。"
        "answer 控制在 250 字以内；suggestion 控制在 120 字以内；chart_desc 控制在 120 字以内；"
        "report_markdown 输出精简 markdown 草稿，按『一、财务健康度』『二、成长潜力』『三、风险提示』『四、建议』四段组织。"
        "证据不足时必须明确说明。"
    )

    user_payload = {
        "question": user_question,
        "stock_context": stock_context or {},
        "analysis_summary": analysis_summary or {},
        "chart_context": chart_context or [],
        "history": history_payload,
        "evidence_items": evidence_items[:6],
    }

    user_content = json.dumps(user_payload, ensure_ascii=False)

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


__all__ = ["build_chat_messages"]