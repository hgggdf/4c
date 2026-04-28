from __future__ import annotations

import json
import logging
import re
from typing import Any

from agent.integration.clarification_detector import detect_clarification
from agent.integration.langgraph_agent import LangGraphAgent
from agent.llm_clients import KimiClient
from agent.session_memory import get_session_memory_cache
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
        "attribution_analysis": "归因分析",
        "butterfly_analysis": "蝴蝶效应",
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

        "attribution_analysis": """\
当前任务：归因分析
请按以下框架拆解分析：
1. 核心指标变动概述（营收/利润/股价的涨跌幅度与时间段）
2. 内部因素归因（产品结构变化、成本变动、研发进展、管理层决策）
3. 外部因素归因（行业政策、集采影响、市场竞争、宏观环境）
4. 关键驱动因子排序（按影响程度从高到低）
5. 后续跟踪建议（需持续关注的指标与催化剂）""",

        "butterfly_analysis": """\
当前任务：蝴蝶效应分析
请按以下框架逐层推演宏观事件的传导链路：
1. 事件解读（事件性质、严重程度、影响时间窗口）
2. 宏观层传导（对GDP、利率、汇率、通胀等宏观变量的影响）
3. 行业层传导（受影响的行业板块、传导机制、影响程度排序）
4. 公司层传导（具体受影响的上市公司、影响路径）
5. 风险提示（需警惕的连锁反应与尾部风险）
6. 投资机会（可能受益的行业与标的）""",
    }

    MODE_DOC_TYPES = {
        "company_analysis": ["announcement", "financial_note", "news", "report"],
        "financial_analysis": ["financial_note", "announcement", "report"],
        "pipeline_analysis": ["announcement", "news", "report"],
        "risk_warning": ["announcement", "news"],
        "industry_compare": ["news", "report", "financial_note"],
        "report_generation": ["announcement", "financial_note", "news", "report"],
        "attribution_analysis": ["financial_note", "announcement", "news", "report"],
        "butterfly_analysis": ["news", "report"],
    }

    def __init__(self) -> None:
        self.container = ServiceContainer.build_default()
        self.llm_client = KimiClient()
        self.tool_agent = LangGraphAgent()
        self._memory = get_session_memory_cache()

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
                        "source_url": r.source_url or "",
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
                    "source_url": a.source_url or "",
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
                        "source_url": r.source_url or "",
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
                elif event_type in ("answer_chunk", "answer_done", "synthesizing"):
                    yield event
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
                if stock_context:
                    template = template.replace("[公司名]", stock_context.get("stock_name", "[公司名]"))
                system_lines.extend(["", template])
            else:
                system_lines.extend([
                    "",
                    f"当前功能模式：{self.MODE_TITLES.get(selected_mode, selected_mode)}",
                    "请严格围绕该模式作答，输出对应维度的结论、依据与建议。",
                ])

        financial_text: str | None = None
        if stock_context:
            system_lines.append("")
            system_lines.append(
                f"当前关注标的：{stock_context.get('stock_name', '')} ({stock_context.get('stock_code', '')})"
            )

            financial_text = self._fetch_financial_context(stock_context.get("stock_code", ""))
            if financial_text:
                system_lines.append("")
                system_lines.append("以下是该公司的真实财务数据（来自数据库 financial_hot 表），请在分析中直接引用：")
                system_lines.append(financial_text)

        if evidence_items:
            system_lines.append("")
            system_lines.append("相关证据材料：")
            for idx, ev in enumerate(evidence_items, 1):
                system_lines.append(
                    f"{idx}. [{ev['kind']}] {ev['title']} ({ev['date']})"
                )
                system_lines.append(f"   {ev['summary']}")
        elif stock_context and not financial_text:
            system_lines.append("")
            system_lines.append(
                "⚠️ 数据缺失警告：本地数据库中没有该标的的任何研报、公告、新闻或财务记录。"
            )
            system_lines.append(
                "你必须直接告知用户「本系统暂无该公司的本地数据，无法进行基于真实文件的分析」，"
                "并说明用户可以通过哪些渠道自行获取（如东方财富、Wind 等）。"
                "严禁基于训练知识编造分析结论、数据或研报内容。"
            )
        elif stock_context and financial_text and not evidence_items:
            system_lines.append("")
            system_lines.append(
                "注意：本地暂无该公司的研报、公告或新闻记录，但上方已提供真实财务数据。"
                "请基于财务数据进行分析，不要声称缺乏数据。"
            )

        return "\n".join(system_lines)

    def _fetch_financial_context(self, stock_code: str) -> str | None:
        """从 financial_hot 查询结构化财务数据，格式化为文本注入 system prompt。"""
        if not stock_code:
            return None
        try:
            from agent.tools.financial_tools import get_financial_summary
            data = get_financial_summary(stock_code, period_count=4)
            periods = data.get("periods") or []
            if not periods:
                return None

            lines: list[str] = []
            for p in periods:
                label = f"{p.get('fiscal_year', '')}年 {p.get('report_date', '')} ({p.get('report_type', '')})"
                parts = [f"【{label}】"]

                def _fmt(val, unit="元"):
                    if val is None:
                        return "N/A"
                    if isinstance(val, float) and abs(val) >= 1e8:
                        return f"{val / 1e8:.2f}亿{unit}"
                    if isinstance(val, float) and abs(val) >= 1e4:
                        return f"{val / 1e4:.2f}万{unit}"
                    return f"{val}{unit}"

                def _pct(val):
                    if val is None:
                        return "N/A"
                    return f"{val * 100:.2f}%"

                parts.append(f"营业收入: {_fmt(p.get('revenue'))}")
                parts.append(f"营业成本: {_fmt(p.get('operating_cost'))}")
                parts.append(f"毛利润: {_fmt(p.get('gross_profit'))}")
                parts.append(f"毛利率: {_pct(p.get('gross_margin'))}")
                parts.append(f"销售费用: {_fmt(p.get('selling_expense'))}")
                parts.append(f"管理费用: {_fmt(p.get('admin_expense'))}")
                parts.append(f"研发费用: {_fmt(p.get('rd_expense'))}")
                parts.append(f"营业利润: {_fmt(p.get('operating_profit'))}")
                parts.append(f"净利润: {_fmt(p.get('net_profit'))}")
                parts.append(f"扣非净利润: {_fmt(p.get('net_profit_deducted'))}")
                parts.append(f"每股收益: {p.get('eps') or 'N/A'}元")
                parts.append(f"总资产: {_fmt(p.get('total_assets'))}")
                parts.append(f"总负债: {_fmt(p.get('total_liabilities'))}")
                parts.append(f"经营现金流: {_fmt(p.get('operating_cashflow'))}")
                parts.append(f"投资现金流: {_fmt(p.get('investing_cashflow'))}")
                parts.append(f"筹资现金流: {_fmt(p.get('financing_cashflow'))}")
                parts.append(f"净利率: {_pct(p.get('net_margin'))}")
                parts.append(f"ROE: {_pct(p.get('roe'))}")
                lines.append(" | ".join(parts))

            return "\n".join(lines)
        except Exception as exc:
            logger.debug("_fetch_financial_context failed for %s: %s", stock_code, exc)
            return None

    def _compress_history(self, messages: list[dict[str, str]]) -> str:
        """用 Kimi 将旧消息压缩成摘要，供记忆缓存调用。"""
        if not self.llm_client.is_configured():
            return ""
        compress_prompt = [
            {
                "role": "system",
                "content": (
                    "你是对话摘要助手。请将以下对话历史压缩成一段简洁的中文摘要（200字以内），"
                    "保留关键结论、提及的公司/股票代码、分析结果和用户的核心诉求。"
                    "不要包含无关细节。"
                ),
            },
            {
                "role": "user",
                "content": "\n".join(
                    f"[{m['role']}] {m['content']}" for m in messages
                ),
            },
        ]
        return self.llm_client.chat(compress_prompt, temperature=1.0, max_tokens=300)

    def build_messages(
        self,
        question: str,
        history: list[dict[str, Any]] | None,
        targets: list[dict[str, Any]] | None,
        current_stock_code: str | None,
        selected_mode: str | None = None,
        *,
        session_id: int | None = None,
        db_messages: list[dict[str, str]] | None = None,
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

        # 优先用数据库消息 + 记忆缓存；回退到前端传来的 history
        if session_id is not None and db_messages is not None:
            summary, recent = self._memory.build_history(
                session_id,
                db_messages,
                llm_compress_fn=self._compress_history,
            )
            if summary:
                messages.append({"role": "system", "content": summary})
            for item in recent:
                role = str(item.get("role") or "user").strip() or "user"
                content = str(item.get("content") or "").strip()
                if content:
                    messages.append({"role": role, "content": content})
        else:
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
        session_id: int | None = None,
        db_messages: list[dict[str, str]] | None = None,
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
            yield {
                "type": "doc_preview",
                "title": ev.get("title", ""),
                "kind": ev.get("kind", ""),
                "date": ev.get("date", ""),
                "file_name": ev.get("file_name", ""),
                "source_url": ev.get("source_url", ""),
                "summary": ev.get("summary", ""),
            }
            imgs = ev.get("images") or []
            if imgs:
                doc_images_for_llm.extend(imgs[:1])

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
            yield {"type": "error", "message": "Kimi API 未配置，请在 backend/.env 中设置 KIMI_API_KEY、KIMI_BASE_URL 和 KIMI_MODEL。"}
            return

        # report_generation 模式：用本地数据生成带图表的结构化报告
        if selected_mode == "report_generation" and stock_context:
            report = self._build_report_with_charts(stock_context, evidence_items)
            if report:
                yield {"type": "answer", "content": report}
                return

        # industry_compare 模式：用本地数据生成多指标对比可视化
        if selected_mode == "industry_compare":
            compare_codes = [
                str(t.get("symbol") or "").strip()
                for t in (targets or [])
                if str(t.get("type") or "stock") == "stock" and t.get("symbol")
            ]
            if stock_context:
                sc = stock_context.get("stock_code")
                if sc and sc not in compare_codes:
                    compare_codes.insert(0, sc)
            report = self._build_industry_compare_charts(compare_codes or None)
            if report:
                yield {"type": "answer", "content": report}
                return
            # 本地数据不足，告知用户后 fallback 到 LLM
            yield {
                "type": "status",
                "content": "本地数据库暂无足够的对比数据，将由 AI 基于知识库进行分析…",
            }

        messages = self.build_messages(
            question, history, targets, current_stock_code, selected_mode=selected_mode,
            session_id=session_id, db_messages=db_messages,
        )

        answer_chunks: list[str] = []
        try:
            max_tokens = 4096 if selected_mode == "report_generation" else 2048
            for chunk in self.llm_client.chat_stream(
                messages, temperature=1.0, max_tokens=max_tokens
            ):
                answer_chunks.append(chunk)
                yield {"type": "answer_chunk", "content": str(chunk)}
        except Exception as exc:
            logger.exception("DialogueAgent chat_stream error")
            yield {"type": "error", "message": f"对话异常: {exc}"}
            return

        # 流结束后把本轮问答追加到记忆缓存，下轮无需重查数据库
        if session_id is not None and answer_chunks:
            self._memory.append(session_id, "user", question)
            self._memory.append(session_id, "assistant", "".join(answer_chunks))

    # 对比指标列表：(指标名, 单位, 是否越高越好)
    _COMPARE_METRICS = [
        ("毛利率",           "%",  True),
        ("净利率",           "%",  True),
        ("ROE",              "%",  True),
        ("资产负债率",       "%",  False),
        ("研发费用率",       "%",  True),
        ("营业总收入增长率", "%",  True),
        ("净利润增长率",     "%",  True),
    ]

    def _build_industry_compare_charts(
        self,
        stock_codes: list[str] | None,
    ) -> str | None:
        from app.router.analysis_service import AnalysisService
        from app.core.database.models.company import Company
        from sqlalchemy import select as sa_select
        svc = AnalysisService()
        metric_results: list[dict] = []
        company_names: dict[str, str] = {}

        # 1家公司时，从数据库补充同行业其他公司（最多取同行业前8家）
        resolved_codes = list(stock_codes or [])
        try:
            with self.container.ctx.session() as db:
                if len(resolved_codes) == 1:
                    solo = db.execute(
                        sa_select(Company).where(Company.stock_code == resolved_codes[0])
                    ).scalar_one_or_none()
                    if solo and solo.industry_level2:
                        peers = db.execute(
                            sa_select(Company)
                            .where(
                                Company.industry_level2 == solo.industry_level2,
                                Company.stock_code != resolved_codes[0],
                            )
                            .order_by(Company.stock_code.asc())
                            .limit(7)
                        ).scalars().all()
                        resolved_codes += [p.stock_code for p in peers]

                for metric, unit, higher_better in self._COMPARE_METRICS:
                    try:
                        res = svc.compare_metric(db, metric, 2024, resolved_codes or None)
                        data = res.get("data") or []
                        if not data:
                            continue
                        for item in data:
                            company_names[item["stock_code"]] = item["stock_name"]
                        metric_results.append({
                            "metric": metric,
                            "unit": unit,
                            "higher_better": higher_better,
                            "data": data,
                        })
                    except Exception:
                        pass
        except Exception as exc:
            logger.debug("_build_industry_compare_charts db error: %s", exc)

        if not metric_results or not company_names:
            return None

        companies = list(company_names.values())
        codes = list(company_names.keys())
        lines: list[str] = []

        # 标题：区分"指定公司"和"全库"两种情况
        if stock_codes:
            title_companies = "、".join(companies[:6]) + ("等" if len(companies) > 6 else "")
            lines.append(f"# 行业对比分析：{title_companies}\n")
        else:
            lines.append("# 行业对比分析：全库公司\n")
        lines.append(
            f"> 数据来源：本地财务热表（FinancialHot）· 2024年度 · "
            f"共 {len(companies)} 家公司：{'、'.join(companies[:8])}{'等' if len(companies) > 8 else ''}\n"
        )

        # ── 一、综合评分排名 ──────────────────────────────────────
        lines.append("## 一、综合评分排名\n")
        # 对每家公司计算综合得分（各指标排名均值）
        score_map: dict[str, float] = {c: 0.0 for c in codes}
        count_map: dict[str, int] = {c: 0 for c in codes}
        for mr in metric_results:
            ranked = [item["stock_code"] for item in mr["data"]]
            n = len(ranked)
            for rank, code in enumerate(ranked):
                if code in score_map:
                    # 排名越靠前得分越高（higher_better 已在 compare_metric 里排好序）
                    score_map[code] += (n - rank) / n * 100
                    count_map[code] += 1
        final_scores = {
            c: round(score_map[c] / count_map[c], 1) if count_map[c] else 0
            for c in codes
        }
        sorted_codes = sorted(codes, key=lambda c: final_scores[c], reverse=True)
        sorted_names = [company_names[c] for c in sorted_codes]
        sorted_scores = [final_scores[c] for c in sorted_codes]

        rank_chart = {
            "_title": "综合竞争力评分",
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": sorted_names, "axisLabel": {"rotate": 30}},
            "yAxis": {"type": "value", "name": "综合得分", "max": 100},
            "series": [{
                "type": "bar",
                "data": sorted_scores,
                "itemStyle": {"color": {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                    "colorStops": [{"offset": 0, "color": "#4ba99a"}, {"offset": 1, "color": "#6366f1"}]}},
                "label": {"show": True, "position": "top", "formatter": "{c}"},
            }],
        }
        lines.append(f":::chart\n{json.dumps(rank_chart, ensure_ascii=False)}\n:::\n")

        lines.append("| 排名 | 公司 | 综合得分 |")
        lines.append("|------|------|----------|")
        for i, code in enumerate(sorted_codes):
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}"
            lines.append(f"| {medal} | {company_names[code]}（{code}） | {final_scores[code]} |")
        lines.append("")

        # ── 二、关键指标横向对比（每个指标一张柱状图）────────────
        lines.append("## 二、关键指标横向对比\n")
        for mr in metric_results:
            metric = mr["metric"]
            unit = mr["unit"]
            data = mr["data"]
            names = [item["stock_name"] for item in data]
            values = [item["value"] for item in data]

            bar_chart = {
                "_title": f"{metric}对比（{unit}）",
                "tooltip": {"trigger": "axis", "formatter": f"{{b}}<br/>{metric}: {{c}}{unit}"},
                "xAxis": {"type": "category", "data": names, "axisLabel": {"rotate": 30}},
                "yAxis": {"type": "value", "name": f"{metric}（{unit}）"},
                "series": [{
                    "type": "bar",
                    "data": values,
                    "itemStyle": {"color": "#4ba99a"},
                    "label": {"show": True, "position": "top", "formatter": f"{{c}}{unit}"},
                }],
            }
            lines.append(f":::chart\n{json.dumps(bar_chart, ensure_ascii=False)}\n:::\n")

        # ── 三、多指标雷达对比（取前5家）────────────────────────
        lines.append("## 三、多维度雷达对比\n")
        top5_codes = sorted_codes[:5]
        top5_names = [company_names[c] for c in top5_codes]

        # 归一化：每个指标按最大值归一化到0-100
        radar_indicators = []
        series_data = {c: [] for c in top5_codes}
        for mr in metric_results:
            metric = mr["metric"]
            data_map = {item["stock_code"]: item["value"] for item in mr["data"]}
            vals = [data_map.get(c, 0) for c in top5_codes]
            max_val = max(abs(v) for v in vals) if vals else 1
            if max_val == 0:
                max_val = 1
            radar_indicators.append({"name": metric, "max": round(max_val * 1.2, 1)})
            for c in top5_codes:
                raw = data_map.get(c, 0)
                # 对于越低越好的指标，反转归一化
                if not mr["higher_better"]:
                    raw = max_val - raw if raw <= max_val else 0
                series_data[c].append(round(raw, 2))

        radar_series = [
            {"value": series_data[c], "name": company_names[c]}
            for c in top5_codes
        ]
        radar_chart = {
            "_title": "多维度竞争力雷达（前5家）",
            "legend": {"data": top5_names},
            "radar": {"indicator": radar_indicators},
            "series": [{"type": "radar", "data": radar_series}],
        }
        lines.append(f":::chart\n{json.dumps(radar_chart, ensure_ascii=False)}\n:::\n")

        # ── 四、详细数据表 ────────────────────────────────────────
        lines.append("## 四、详细数据明细\n")
        metric_names = [mr["metric"] for mr in metric_results]
        header = "| 公司 | " + " | ".join(metric_names) + " |"
        sep = "|------|" + "|".join(["------"] * len(metric_names)) + "|"
        lines.append(header)
        lines.append(sep)
        for code in sorted_codes:
            name = company_names[code]
            row_vals = []
            for mr in metric_results:
                data_map = {item["stock_code"]: item for item in mr["data"]}
                item = data_map.get(code)
                if item:
                    row_vals.append(f"{item['value']}{item['unit']}")
                else:
                    row_vals.append("—")
            lines.append(f"| {name} | " + " | ".join(row_vals) + " |")
        lines.append("")
        lines.append(f"> 来源：本地财务热表（FinancialHot）· 2024年度\n")
        lines.append("\n---\n*本对比基于本地数据库自动生成，仅供参考。*")

        return "\n".join(lines)

    def _build_report_with_charts(
        self,
        stock_context: dict[str, Any],
        evidence_items: list[dict[str, Any]],
    ) -> str | None:
        stock_code = stock_context.get("stock_code")
        stock_name = stock_context.get("stock_name") or stock_code
        industry1 = stock_context.get("industry_level1") or ""
        industry2 = stock_context.get("industry_level2") or ""
        if not stock_code:
            return None

        from app.router.analysis_service import AnalysisService
        analysis_svc = AnalysisService()
        analysis_summary: dict[str, Any] | None = None
        chart_context: list[dict[str, Any]] = []

        try:
            with self.container.ctx.session() as db:
                result = analysis_svc.diagnose(db, stock_code)
                if result:
                    analysis_summary = {
                        "total_score": result.total_score,
                        "level": result.level,
                        "strengths": result.strengths,
                        "weaknesses": result.weaknesses,
                        "suggestion": result.suggestion,
                        "dimensions": [
                            {"name": d.name, "score": d.score, "comment": d.comment}
                            for d in result.dimensions
                        ],
                    }
                for metric in ("营业总收入", "净利润"):
                    try:
                        trend = analysis_svc.get_metric_trend(db, stock_code, metric)
                        points = [
                            {"year": str(p["year"]), "value": p["value"]}
                            for p in trend.get("trend") or []
                        ]
                        if points:
                            chart_context.append({"metric": metric, "points": points})
                    except Exception:
                        pass
        except Exception as exc:
            logger.debug("_build_report_with_charts db error: %s", exc)

        if not analysis_summary and not chart_context:
            return None

        # 按类型分拣证据
        reports = [e for e in evidence_items if e.get("kind") == "report"]
        announcements = [e for e in evidence_items if e.get("kind") == "announcement"]
        news_items = [e for e in evidence_items if e.get("kind") == "news"]
        pipeline_evidence = [e for e in evidence_items if e.get("kind") in ("announcement", "report")]

        suggestion_raw = (analysis_summary or {}).get("suggestion") or ""
        lines: list[str] = [f"# {stock_name} 投研报告\n"]
        lines.append(f"> 数据来源：本地数据库（财务热表 / 公告 / 研报）｜股票代码：{stock_code}｜生成时间：自动\n")

        # ── 一、公司概况 ──────────────────────────────────────────
        lines.append("## 一、公司概况\n")
        industry_str = "、".join(filter(None, [industry1, industry2])) or "医药行业"
        lines.append(f"**{stock_name}**（{stock_code}）属于 **{industry_str}** 板块。\n")
        if reports:
            r = reports[0]
            lines.append(f"最新研报（{r.get('source','')} · {r.get('date','')}）摘要：{_compact_text(r.get('summary',''), limit=150)}\n")
            lines.append(f"> 来源：{r.get('source','研报')} · {r.get('date','')}\n")
        elif announcements:
            a = announcements[0]
            lines.append(f"近期公告（{a.get('date','')}）：{_compact_text(a.get('summary',''), limit=150)}\n")
            lines.append(f"> 来源：公告 · {a.get('date','')}\n")
        else:
            lines.append("暂无本地研报/公告数据，建议补充后重新生成。\n")

        # ── 二、财务分析 ──────────────────────────────────────────
        lines.append("## 二、财务分析\n")
        if analysis_summary:
            score = analysis_summary.get("total_score", "N/A")
            level = analysis_summary.get("level", "未知")
            lines.append(f"综合财务评分 **{score}** 分，评级 **{level}**。\n")
            dims = analysis_summary.get("dimensions") or []
            if dims:
                dim_names = [d.get("name", "") for d in dims]
                dim_scores = [d.get("score", 0) for d in dims]
                radar_chart = {
                    "_title": "多维度评分雷达图",
                    "radar": {"indicator": [{"name": n, "max": 100} for n in dim_names]},
                    "series": [{"type": "radar", "data": [{"value": dim_scores, "name": stock_name}], "areaStyle": {"opacity": 0.25}}],
                    "legend": {"data": [stock_name]},
                }
                lines.append(f":::chart\n{json.dumps(radar_chart, ensure_ascii=False)}\n:::\n")
                lines.append("| 维度 | 得分 | 点评 |")
                lines.append("|------|------|------|")
                for d in dims:
                    lines.append(f"| {d.get('name','')} | {d.get('score','N/A')} | {d.get('comment','--')} |")
                lines.append("")
            lines.append(f"> 来源：本地财务热表（FinancialHot）· 股票代码 {stock_code}\n")
        else:
            lines.append("暂无本地财务评分数据。\n")

        # 营收与利润趋势图
        rev = next((c for c in chart_context if c.get("metric") == "营业总收入"), None)
        prof = next((c for c in chart_context if c.get("metric") == "净利润"), None)
        if rev or prof:
            dates = [p["year"] for p in (rev or prof).get("points", [])]
            series = []
            if rev:
                series.append({"name": "营业总收入", "type": "bar", "data": [p["value"] for p in rev["points"]], "yAxisIndex": 0})
            if prof:
                series.append({"name": "净利润", "type": "line", "data": [p["value"] for p in prof["points"]], "yAxisIndex": 1, "smooth": True})
            trend_chart = {
                "_title": "营收与利润趋势",
                "tooltip": {"trigger": "axis"},
                "legend": {"data": [s["name"] for s in series]},
                "xAxis": {"type": "category", "data": dates},
                "yAxis": [
                    {"type": "value", "name": "营收(万元)", "position": "left"},
                    {"type": "value", "name": "净利润(万元)", "position": "right"},
                ],
                "series": series,
            }
            lines.append(f":::chart\n{json.dumps(trend_chart, ensure_ascii=False)}\n:::\n")
            lines.append(f"> 来源：本地财务热表（FinancialHot）· 股票代码 {stock_code}\n")

        # ── 三、研发管线分析 ──────────────────────────────────────
        lines.append("## 三、研发管线分析\n")
        pipeline_found = False
        for ev in pipeline_evidence[:4]:
            summary = ev.get("summary", "")
            title = ev.get("title", "")
            date = ev.get("date", "")
            kind_label = "研报" if ev.get("kind") == "report" else "公告"
            # 只展示含管线关键词的证据
            pipeline_keywords = ["管线", "临床", "获批", "申报", "IND", "NDA", "适应症", "研发", "在研", "新药"]
            if any(kw in summary or kw in title for kw in pipeline_keywords):
                lines.append(f"- **{title}**（{date}）：{_compact_text(summary, limit=120)}")
                lines.append(f"  > 来源：{kind_label} · {ev.get('source','')} · {date}")
                pipeline_found = True
        if not pipeline_found:
            lines.append("暂无本地管线相关公告/研报，建议补充数据后重新生成。\n")
        lines.append("")

        # ── 四、风险提示 ──────────────────────────────────────────
        lines.append("## 四、风险提示\n")
        weaknesses = (analysis_summary or {}).get("weaknesses") or []
        if weaknesses:
            lines.append("**财务层面风险：**\n")
            for w in weaknesses[:3]:
                lines.append(f"- {w}")
            lines.append(f"\n> 来源：本地财务评分模型 · 股票代码 {stock_code}\n")
        for ev in (announcements + news_items)[:3]:
            title = ev.get("title", "")
            summary = ev.get("summary", "")
            date = ev.get("date", "")
            risk_keywords = ["风险", "处罚", "调查", "集采", "降价", "诉讼", "违规", "警示"]
            if any(kw in summary or kw in title for kw in risk_keywords):
                lines.append(f"- **{title}**（{date}）：{_compact_text(summary, limit=100)}")
                lines.append(f"  > 来源：{'公告' if ev.get('kind')=='announcement' else '新闻'} · {date}")
        lines.append("")

        # ── 五、投资建议 ──────────────────────────────────────────
        lines.append("## 五、投资建议\n")
        score_val = (analysis_summary or {}).get("total_score") or 0
        if score_val >= 80:
            rating, rating_reason = "买入", "财务健康度优秀，各维度均衡"
        elif score_val >= 65:
            rating, rating_reason = "增持", "财务状况良好，具备持续成长潜力"
        elif score_val >= 45:
            rating, rating_reason = "中性", "财务表现一般，需关注改善进度"
        else:
            rating, rating_reason = "减持", "财务存在明显弱项，需谨慎观察"

        lines.append(f"**评级：{rating}**\n")
        lines.append(f"**核心逻辑：** {rating_reason}。\n")

        strengths = (analysis_summary or {}).get("strengths") or []
        if strengths:
            lines.append("**主要优势：**\n")
            for s in strengths[:3]:
                lines.append(f"- {s}")
            lines.append("")

        if suggestion_raw:
            lines.append("**改进建议：**\n")
            for part in suggestion_raw.split("；"):
                part = part.strip()
                if part:
                    lines.append(f"- {part}")
            lines.append("")

        lines.append("**主要风险：**\n")
        if weaknesses:
            for w in weaknesses[:2]:
                lines.append(f"- {w}")
        else:
            lines.append("- 请结合最新公告与行业政策动态综合判断")
        lines.append("")
        lines.append(f"> 来源：本地财务评分模型 · 股票代码 {stock_code}\n")
        lines.append("\n---\n*本报告基于本地数据库自动生成，仅供参考，不构成投资建议。*")

        return "\n".join(lines)


__all__ = ["DialogueAgent"]
