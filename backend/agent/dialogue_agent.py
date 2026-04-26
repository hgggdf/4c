from __future__ import annotations

import logging
import re
from typing import Any

from agent.integration.langgraph_agent import LangGraphAgent
from agent.llm_clients import KimiClient
from app.service.container import ServiceContainer
from app.service.requests import SearchRequest

logger = logging.getLogger(__name__)


def _compact_text(value: Any, *, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


class DialogueAgent:
    """基于 Kimi 的流式对话 Agent，保留股票上下文与证据检索能力。"""

    framework = "kimi"
    agent_mode = "kimi-dialogue"

    MODE_TITLES = {
        "company_analysis": "企业运营评估",
        "financial_analysis": "财务分析",
        "pipeline_analysis": "管线分析",
        "risk_warning": "风险预警",
        "industry_compare": "行业对比",
        "report_generation": "生成报告",
    }

    MODE_DOC_TYPES = {
        "company_analysis": ["announcement", "financial_note", "news", "report"],
        "financial_analysis": ["financial_note", "announcement", "report"],
        "pipeline_analysis": ["announcement", "news", "report"],
        "risk_warning": ["announcement", "news"],
        "industry_compare": ["news", "report", "financial_note"],
        "report_generation": ["announcement", "financial_note", "news", "report"],
    }

    def __init__(self) -> None:
        self.container = ServiceContainer.build_default()
        self.llm_client = KimiClient()
        self.tool_agent = LangGraphAgent()

    def is_configured(self) -> bool:
        return self.llm_client.is_configured()

    # ── 股票上下文解析（复用 GLMMinimalAgent 逻辑）─────────────────────────

    def _resolve_stock_context(
        self,
        question: str,
        *,
        targets: list[dict[str, Any]] | None,
        current_stock_code: str | None,
    ) -> dict[str, Any] | None:
        for item in targets or []:
            if str(item.get("type") or "stock") != "stock":
                continue
            target = str(item.get("symbol") or item.get("name") or "").strip()
            resolved = self._resolve_company_target(target)
            if resolved:
                return resolved

        resolved = self._resolve_company_target(question)
        if resolved:
            return resolved

        if current_stock_code:
            return self._resolve_company_target(current_stock_code)
        return None

    def _resolve_company_target(self, value: str) -> dict[str, Any] | None:
        target = str(value or "").strip()
        if not target:
            return None

        if re.fullmatch(r"\d{6}", target):
            info = self.container.company.get_company_basic_info(target)
            if info.success and info.data:
                data = info.data
                return {
                    "stock_code": data.get("stock_code"),
                    "stock_name": data.get("stock_name"),
                    "industry_level1": data.get("industry_level1"),
                    "industry_level2": data.get("industry_level2"),
                }

        resolved = self.container.company.resolve_company(target)
        if not resolved.success or not resolved.data:
            return None
        first = resolved.data[0]
        return {
            "stock_code": first.get("stock_code"),
            "stock_name": first.get("stock_name"),
            "industry_level1": first.get("industry_level1"),
            "industry_level2": first.get("industry_level2"),
        }

    # ── 证据收集（复用 GLMMinimalAgent 逻辑）──────────────────────────────

    def _collect_evidence(
        self,
        question: str,
        stock_context: dict[str, Any] | None,
        *,
        selected_mode: str | None = None,
    ) -> list[dict[str, Any]]:
        stock_code = stock_context.get("stock_code") if stock_context else None
        items: list[dict[str, Any]] = []

        allowed_doc_types = self.MODE_DOC_TYPES.get(selected_mode or "", ["announcement", "financial_note", "news", "report"])
        search_plan = [
            ("announcement", self.container.retrieval.search_announcements, 2),
            ("financial_note", self.container.retrieval.search_financial_notes, 2),
            ("news", self.container.retrieval.search_news, 1),
            ("report", self.container.retrieval.search_reports, 2),
        ]

        for doc_type, handler, limit in search_plan:
            if doc_type not in allowed_doc_types:
                continue
            try:
                result = handler(
                    SearchRequest(query=question, stock_code=stock_code, top_k=limit)
                )
            except Exception as exc:
                logger.debug("Evidence search failed for %s: %s", doc_type, exc)
                continue
            if not result.success or not result.data:
                continue
            for item in result.data.get("items") or []:
                compressed = self._compress_retrieval_item(
                    item, default_kind=doc_type
                )
                if compressed:
                    items.append(compressed)

        deduped: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for item in items:
            key = (
                str(item.get("kind") or ""),
                str(item.get("title") or ""),
                str(item.get("date") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
            if len(deduped) >= 6:
                break
        return deduped

    def _compress_retrieval_item(
        self,
        item: dict[str, Any],
        *,
        default_kind: str,
    ) -> dict[str, Any] | None:
        metadata = item.get("metadata") or {}
        source_record = item.get("source_record") or {}
        text = item.get("text") or ""
        title = (
            metadata.get("title")
            or source_record.get("title")
            or source_record.get("note_type")
            or default_kind
        )
        date = (
            metadata.get("publish_date")
            or metadata.get("date")
            or source_record.get("publish_date")
            or source_record.get("report_date")
            or source_record.get("publish_time")
            or ""
        )
        source = (
            metadata.get("source_type")
            or source_record.get("source_type")
            or source_record.get("source_name")
            or default_kind
        )
        summary = _compact_text(text, limit=180)
        if not title or not summary:
            return None
        return {
            "kind": metadata.get("doc_type") or default_kind,
            "title": str(title),
            "date": str(date),
            "source": str(source),
            "summary": summary,
        }

    def _chat_stream_with_tool_autonomy(
        self,
        question: str,
        *,
        history: list[dict[str, Any]] | None,
        targets: list[dict[str, Any]] | None,
        current_stock_code: str | None,
        selected_mode: str | None = None,
        system_context: str | None = None,
    ):
        if not self.tool_agent.is_configured():
            yield {
                "type": "status",
                "content": "Kimi 工具调用模型未配置，请检查 backend/.env 中的 KIMI_API_KEY、KIMI_BASE_URL 和 KIMI_MODEL。",
            }
            return

        try:
            for event in self.tool_agent.stream(
                question,
                history=history,
                system_context=system_context,
            ):
                event_type = event.get("type")
                if event_type == "tool_call":
                    yield {
                        "type": "tool_call",
                        "tool": event.get("tool"),
                        "args": event.get("args"),
                    }
                elif event_type == "tool_result":
                    yield {
                        "type": "tool_result",
                        "tool": event.get("tool"),
                        "content": event.get("content"),
                    }
                elif event_type == "status":
                    yield {
                        "type": "status",
                        "content": event.get("content"),
                    }
                elif event_type == "clarification":
                    yield {
                        "type": "clarification",
                        "question": event.get("question"),
                    }
                elif event_type == "answer":
                    yield {
                        "type": "answer",
                        "content": event.get("content") or "",
                    }
        except Exception as exc:
            logger.exception("DialogueAgent tool autonomy stream error")
            yield {
                "type": "status",
                "content": f"工具自主调用异常: {exc}",
            }

    # ── 对话构建与流式输出 ────────────────────────────────────────────────

    def _build_system_context(
        self,
        question: str,
        *,
        selected_mode: str | None,
        stock_context: dict[str, Any] | None,
        evidence_items: list[dict[str, Any]],
    ) -> str:
        system_lines = [
            "你是「医药投研智能助手」，由 Moonshot Kimi 大模型驱动，专注于医药行业的投资研究分析。",
            "",
            "你的能力包括：",
            "1. 分析医药企业的财务健康度、研发管线、商业化能力",
            "2. 解读行业政策、市场动态、竞争格局",
            "3. 基于公告、财报、新闻等证据材料给出客观判断",
            "4. 回答一般性投资研究问题",
            "",
            "回答规则：",
            "- 基于提供的证据作答，禁止编造数据、公告内容或公司信息",
            "- 证据不足时明确说明，不猜测、不捏造",
            "- 使用中文回答，保持专业、简洁、有逻辑",
            "- 可适当使用 Markdown 格式增强可读性",
        ]
        if selected_mode:
            system_lines.extend([
                "",
                f"当前功能模式：{selected_mode}",
                "请严格围绕该模式作答，不要把问题泛化成普通闲聊。",
                "如果模式是公司分析、财务分析、管线分析、风险预警、行业对比或生成报告，请输出对应维度的结论、依据与下一步建议。",
            ])

        if stock_context:
            system_lines.append("")
            system_lines.append(
                f"当前关注标的：{stock_context.get('stock_name', '')} ({stock_context.get('stock_code', '')})"
            )

        if evidence_items:
            system_lines.append("")
            system_lines.append("相关证据材料：")
            for idx, ev in enumerate(evidence_items, 1):
                system_lines.append(
                    f"{idx}. [{ev['kind']}] {ev['title']} ({ev['date']})"
                )
                system_lines.append(f"   {ev['summary']}")

        return "\n".join(system_lines)

    def build_messages(
        self,
        question: str,
        history: list[dict[str, Any]] | None,
        targets: list[dict[str, Any]] | None,
        current_stock_code: str | None,
        selected_mode: str | None = None,
    ) -> list[dict[str, str]]:
        stock_context = self._resolve_stock_context(
            question,
            targets=targets,
            current_stock_code=current_stock_code,
        )
        evidence_items = (
            self._collect_evidence(question, stock_context, selected_mode=selected_mode)
            if stock_context
            else []
        )
        system_content = self._build_system_context(
            question,
            selected_mode=selected_mode,
            stock_context=stock_context,
            evidence_items=evidence_items,
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_content}
        ]

        for item in (history or [])[-10:]:
            role = str(item.get("role") or "user").strip() or "user"
            content = str(item.get("content") or "").strip()
            if content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": question})
        return messages

    def chat_stream(
        self,
        question: str,
        *,
        history: list[dict[str, Any]] | None = None,
        targets: list[dict[str, Any]] | None = None,
        current_stock_code: str | None = None,
        selected_mode: str | None = None,
        tool_autonomy: bool = False,
    ):
        stock_context = self._resolve_stock_context(
            question,
            targets=targets,
            current_stock_code=current_stock_code,
        )
        evidence_items = (
            self._collect_evidence(question, stock_context, selected_mode=selected_mode)
            if stock_context
            else []
        )
        system_context = self._build_system_context(
            question,
            selected_mode=selected_mode,
            stock_context=stock_context,
            evidence_items=evidence_items,
        )

        if tool_autonomy:
            yield from self._chat_stream_with_tool_autonomy(
                question,
                history=history,
                targets=targets,
                current_stock_code=current_stock_code,
                selected_mode=selected_mode,
                system_context=system_context,
            )
            return

        if not self.is_configured():
            yield "Kimi API 未配置，请在 backend/.env 中设置 KIMI_API_KEY、KIMI_BASE_URL 和 KIMI_MODEL。"
            return

        messages = self.build_messages(
            question, history, targets, current_stock_code, selected_mode=selected_mode
        )

        try:
            yield from self.llm_client.chat_stream(
                messages, temperature=1.0, max_tokens=2048
            )
        except Exception as exc:
            logger.exception("DialogueAgent chat_stream error")
            yield f"\n\n[对话异常: {exc}]"


__all__ = ["DialogueAgent"]
