from __future__ import annotations

import json
import logging
import re
from typing import Any

from agent.integration.clarification_detector import detect_clarification
from agent.integration.langgraph_agent import LangGraphAgent
from agent.llm_clients import KimiClient
from app.service.container import ServiceContainer
from app.service.requests import SearchRequest
from app.service.doc_image_service import get_doc_images

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

    MODE_SYSTEM_TEMPLATES = {
        "company_analysis": """\
当前任务：企业运营评估
请按以下框架输出分析报告：
1. 公司概况（主营业务、市场定位）
2. 核心竞争优势（产品、渠道、技术壁垒）
3. 近期经营动态（重要公告、战略调整）
4. 管理层与治理
5. 综合评价与关注点""",

        "financial_analysis": """\
当前任务：财务分析
请按以下框架输出分析报告：
1. 营收与利润趋势（近4期）
2. 毛利率 / 净利率变化及原因
3. 现金流健康度（经营/投资/筹资）
4. 资产负债结构与偿债能力
5. 关键财务风险提示""",

        "pipeline_analysis": """\
当前任务：研发管线分析
请按以下框架输出分析报告：
1. 在研品种总览（按适应症/阶段分类）
2. 核心品种进展（临床阶段、预计获批时间）
3. 近期获批/申报情况
4. 商业化潜力评估
5. 研发风险与催化剂""",

        "risk_warning": """\
当前任务：风险预警
请按以下框架输出分析报告：
1. 集采风险（已中标/待纳入品种、降价幅度）
2. 监管与合规风险
3. 研发管线失败风险
4. 财务与流动性风险
5. 综合风险评级（高/中/低）及应对建议""",

        "industry_compare": """\
当前任务：行业对比分析
请按以下框架输出分析报告：
1. 行业格局与主要竞争对手
2. 关键财务指标横向对比（营收、利润率、研发投入）
3. 产品管线对比
4. 市场份额与竞争优势对比
5. 相对投资价值判断""",

        "report_generation": """\
当前任务：生成完整投研报告
请按以下框架输出完整报告，内容尽量详尽：

# [公司名] 投研报告

## 一、公司概况
## 二、财务分析
## 三、研发管线
## 四、风险提示
## 五、投资建议
- 评级：买入 / 增持 / 中性 / 减持
- 核心逻辑与目标价区间（如有数据支撑）""",
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

        # 向量检索无数据时，直接从数据库补充最新研报/公告并附带图片
        if stock_code and not deduped:
            deduped = self._collect_db_evidence_with_images(stock_code, selected_mode)

        return deduped

    def _collect_db_evidence_with_images(
        self,
        stock_code: str,
        selected_mode: str | None,
    ) -> list[dict[str, Any]]:
        """直接从数据库查最新研报和公告，附带本地 PDF 图片。"""
        from app.core.database.session import get_db
        from app.core.database.models.research_report_hot import ResearchReportHot
        from app.core.database.models.announcement_hot import AnnouncementHot

        items: list[dict[str, Any]] = []
        try:
            db = next(get_db())

            # 最新研报（最多2条）—— 只查该公司的研报，排除 stock_code=None 的行业研报
            if selected_mode not in ("risk_warning",):
                reports = (
                    db.query(ResearchReportHot)
                    .filter(
                        ResearchReportHot.stock_code == stock_code,
                        ResearchReportHot.scope_type == "company",
                    )
                    .order_by(ResearchReportHot.publish_date.desc())
                    .limit(2)
                    .all()
                )
                for r in reports:
                    date_str = str(r.publish_date) if r.publish_date else ""
                    img_result = get_doc_images(
                        "research_report",
                        stock_code=stock_code,
                        publish_date=date_str,
                        source_url=r.source_url or "",
                        max_pages=2,
                    )
                    item: dict[str, Any] = {
                        "kind": "report",
                        "title": r.title or "研报",
                        "date": date_str,
                        "source": r.report_org or r.source_type or "research_report",
                        "summary": _compact_text(r.summary_text or r.content or "", limit=180),
                    }
                    if img_result["images"]:
                        item["images"] = img_result["images"]
                        item["image_source"] = img_result["source"]
                        item["file_name"] = img_result["file_name"]
                    items.append(item)

            # 最新公告（最多2条）
            announcements = (
                db.query(AnnouncementHot)
                .filter(AnnouncementHot.stock_code == stock_code)
                .order_by(AnnouncementHot.publish_date.desc())
                .limit(2)
                .all()
            )
            for a in announcements:
                date_str = str(a.publish_date) if a.publish_date else ""
                img_result = get_doc_images(
                    "announcement",
                    stock_code=stock_code,
                    publish_date=date_str,
                    source_url=a.source_url or "",
                    max_pages=2,
                )
                item = {
                    "kind": "announcement",
                    "title": a.title or "公告",
                    "date": date_str,
                    "source": a.announcement_type or "announcement",
                    "summary": _compact_text(a.summary_text or a.content or "", limit=180),
                }
                if img_result["images"]:
                    item["images"] = img_result["images"]
                    item["image_source"] = img_result["source"]
                    item["file_name"] = img_result["file_name"]
                items.append(item)

            # 若公司研报为空，补充最新行业研报（scope_type='industry'）
            has_report = any(i["kind"] == "report" for i in items)
            if not has_report and selected_mode not in ("risk_warning",):
                ind_reports = (
                    db.query(ResearchReportHot)
                    .filter(ResearchReportHot.scope_type == "industry")
                    .order_by(ResearchReportHot.publish_date.desc())
                    .limit(2)
                    .all()
                )
                for r in ind_reports:
                    date_str = str(r.publish_date) if r.publish_date else ""
                    img_result = get_doc_images(
                        "research_report",
                        industry_code=r.industry_code or "",
                        publish_date=date_str,
                        source_url=r.source_url or "",
                        max_pages=2,
                    )
                    item = {
                        "kind": "report",
                        "title": r.title or "行业研报",
                        "date": date_str,
                        "source": r.report_org or "industry_report",
                        "summary": _compact_text(r.summary_text or r.content or "", limit=180),
                    }
                    if img_result["images"]:
                        item["images"] = img_result["images"]
                        item["image_source"] = img_result["source"]
                        item["file_name"] = img_result["file_name"]
                    items.append(item)

        except Exception as exc:
            logger.debug("_collect_db_evidence_with_images failed: %s", exc)

        return items

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
            template = self.MODE_SYSTEM_TEMPLATES.get(selected_mode)
            if template:
                system_lines.extend(["", template])
            else:
                system_lines.extend([
                    "",
                    f"当前功能模式：{self.MODE_TITLES.get(selected_mode, selected_mode)}",
                    "请严格围绕该模式作答，输出对应维度的结论、依据与建议。",
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
        elif stock_context:
            # 明确告知 LLM 本地无数据，禁止生成虚假分析
            system_lines.append("")
            system_lines.append(
                "⚠️ 数据缺失警告：本地数据库中没有该标的的任何研报、公告或新闻记录。"
            )
            system_lines.append(
                "你必须直接告知用户「本系统暂无该公司的本地数据，无法进行基于真实文件的分析」，"
                "并说明用户可以通过哪些渠道自行获取（如东方财富、Wind 等）。"
                "严禁基于训练知识编造分析结论、数据或研报内容。"
            )

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
        # ── 澄清检测：问题模糊时先追问，不进入分析流程 ──────────────────
        clarification = detect_clarification(
            question,
            selected_mode=selected_mode,
            history=history,
            targets=targets,
            current_stock_code=current_stock_code,
        )
        if clarification["need_clarification"]:
            yield {
                "type": "clarification",
                "question": clarification["question"],
                "suggestions": clarification["suggestions"],
                "reason": clarification["reason"],
            }
            return

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

        # 把带图片的 evidence 通过 SSE 发给前端展示
        doc_images_for_llm: list[str] = []
        for ev in evidence_items:
            imgs = ev.get("images") or []
            if imgs:
                yield {
                    "type": "doc_preview",
                    "title": ev.get("title", ""),
                    "kind": ev.get("kind", ""),
                    "date": ev.get("date", ""),
                    "file_name": ev.get("file_name", ""),
                    "image_source": ev.get("image_source", ""),
                    "images": imgs,
                }
                doc_images_for_llm.extend(imgs[:1])  # 每份文档取第一页传给 LLM

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

        # 有图片且 Claude 已配置时，优先用 Claude 做视觉分析
        from agent.llm_clients import ClaudeClient
        claude = ClaudeClient()
        if doc_images_for_llm and claude.is_configured():
            try:
                max_tokens = 4096 if selected_mode == "report_generation" else 2048
                result = claude.chat_with_images(
                    question,
                    doc_images_for_llm[:3],
                    system=system_context,
                    max_tokens=max_tokens,
                )
                yield {"type": "answer", "content": result}
            except Exception as exc:
                logger.warning("Claude vision failed, fallback to Kimi: %s", exc)
                messages = self.build_messages(
                    question, history, targets, current_stock_code, selected_mode=selected_mode
                )
                try:
                    max_tokens = 4096 if selected_mode == "report_generation" else 2048
                    yield from self.llm_client.chat_stream(messages, temperature=1.0, max_tokens=max_tokens)
                except Exception as exc2:
                    logger.exception("DialogueAgent chat_stream fallback error")
                    yield f"\n\n[对话异常: {exc2}]"
            return

        messages = self.build_messages(
            question, history, targets, current_stock_code, selected_mode=selected_mode
        )

        try:
            max_tokens = 4096 if selected_mode == "report_generation" else 2048
            yield from self.llm_client.chat_stream(
                messages, temperature=1.0, max_tokens=max_tokens
            )
        except Exception as exc:
            logger.exception("DialogueAgent chat_stream error")
            yield f"\n\n[对话异常: {exc}]"


__all__ = ["DialogueAgent"]
