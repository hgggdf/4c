from __future__ import annotations

import json
import logging
import re
from hashlib import md5
from typing import Any

from agent.llm_clients import KimiClient
from agent.prompts import build_chat_messages
from app.knowledge.store import get_store
from app.service.container import ServiceContainer
from app.service.requests import CacheQueryRequest, CacheSetQueryRequest, SearchRequest

from .entity_resolver import resolve_entities
from .followup_generator import generate_follow_up_questions
from .freshness_router import determine_freshness_strategy
from .medical_adapter import build_medical_analysis
from .mode_resolver import resolve_mode
from .output_builder import build_structured_output
from .preference_profiler import build_preference_profile
from .state import AgentState
from .tool_executor import execute_tool_plan
from .tool_planner import build_tool_plan


logger = logging.getLogger(__name__)
DEFAULT_GLM_MAX_TOKENS = 2000


def _extract_year(text: str) -> int:
    match = re.search(r"(20\d{2})", text or "")
    return int(match.group(1)) if match else 2024


def _compact_text(value: Any, *, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _extract_json_object(text: str) -> dict[str, Any] | None:
    raw = str(text or "").strip()
    if not raw:
        return None

    fenced = re.search(r"```json\s*(\{.*?\})\s*```", raw, flags=re.S)
    if fenced:
        raw = fenced.group(1)

    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return None

    try:
        parsed = json.loads(raw[start:end + 1])
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


class GLMMinimalAgent:
    framework = "kimi"
    agent_mode = "kimi-k2.5"

    def __init__(self) -> None:
        self.container = ServiceContainer.build_default()
        from app.router.analysis_service import AnalysisService

        self.analysis_service = AnalysisService()
        self.llm_client = KimiClient()

    def run(
        self,
        message: str,
        *,
        history: list[dict[str, Any]] | None = None,
        targets: list[dict[str, Any]] | None = None,
        current_stock_code: str | None = None,
        user_id: int | None = None,
        session_id: int | None = None,
        selected_mode: str | None = None,
        frontend_context: dict[str, Any] | None = None,
        followup_from: str | None = None,
        preference_hint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        question = str(message or "").strip()
        state = AgentState(
            user_question=question,
            session_id=session_id,
            user_id=user_id,
            history=list(history or []),
            targets=list(targets or []),
            current_stock_code=current_stock_code,
            selected_mode=selected_mode,
            frontend_context=frontend_context,
            followup_from=followup_from,
            preference_hint=preference_hint,
        )
        state.resolved_mode = resolve_mode(state.user_question, selected_mode=state.selected_mode)
        entity_result = resolve_entities(
            state.user_question,
            history=state.history,
            targets=state.targets,
            current_stock_code=state.current_stock_code,
        )
        state.company_entity = entity_result.get("company_entity")
        state.drug_entity = entity_result.get("drug_entity")
        state.industry_entity = entity_result.get("industry_entity")
        state.time_range = entity_result.get("time_range")
        for warning in entity_result.get("warnings") or []:
            state.warnings.append(warning)
        state.preference_profile = build_preference_profile(
            state.user_question,
            selected_mode=state.resolved_mode,
            preference_hint=state.preference_hint,
            followup_from=state.followup_from,
            time_range=state.time_range,
        )
        freshness_result = determine_freshness_strategy(
            state.user_question,
            selected_mode=state.resolved_mode,
            company_entity=state.company_entity,
            drug_entity=state.drug_entity,
            industry_entity=state.industry_entity,
            time_range=state.time_range,
            preference_profile=state.preference_profile,
        )
        state.freshness_strategy = freshness_result.get("strategy")
        for warning in freshness_result.get("warnings") or []:
            state.warnings.append(warning)
        if state.freshness_strategy != "insufficient":
            state.tool_plan = build_tool_plan(
                state.user_question,
                selected_mode=state.resolved_mode,
                freshness_strategy=state.freshness_strategy,
                company_entity=state.company_entity,
                drug_entity=state.drug_entity,
                industry_entity=state.industry_entity,
                time_range=state.time_range,
                preference_profile=state.preference_profile,
            )
        else:
            state.tool_plan = []
        state.tool_results = execute_tool_plan(
            state.tool_plan,
            dry_run=True,
        )
        for item in state.tool_results or []:
            if item.get("success") is False:
                state.warnings.append({
                    "type": "工具执行失败",
                    "message": item.get("error") or item.get("warning") or "工具执行失败",
                    "detail": {"tool_name": item.get("tool_name")},
                })
        medical_result = build_medical_analysis(
            user_question=state.user_question,
            selected_mode=state.resolved_mode,
            company_entity=state.company_entity,
            drug_entity=state.drug_entity,
            industry_entity=state.industry_entity,
            time_range=state.time_range,
            preference_profile=state.preference_profile,
            freshness_strategy=state.freshness_strategy,
            tool_plan=state.tool_plan,
            tool_results=state.tool_results,
        )
        state.medical_analysis = medical_result.get("medical_analysis")
        state.score_result = medical_result.get("score_result")
        state.key_metrics = medical_result.get("key_metrics") or []
        state.chart_payload = medical_result.get("chart_payload") or []
        state.evidence_list = medical_result.get("evidence_list") or []
        for warning in medical_result.get("warnings") or []:
            state.warnings.append(warning)
        structured_output = build_structured_output(
            selected_mode=state.resolved_mode,
            company_entity=state.company_entity,
            medical_analysis=state.medical_analysis,
            score_result=state.score_result,
            key_metrics=state.key_metrics,
            chart_payload=state.chart_payload,
            evidence_list=state.evidence_list,
            warnings=state.warnings,
        )
        state.summary = structured_output.get("summary")
        state.key_points = structured_output.get("key_points") or []
        state.answer = structured_output.get("answer") or state.answer
        state.follow_up_questions = generate_follow_up_questions(
            user_question=state.user_question,
            selected_mode=state.resolved_mode,
            company_entity=state.company_entity,
            drug_entity=state.drug_entity,
            industry_entity=state.industry_entity,
            warnings=state.warnings,
        )
        stock_context = self._resolve_stock_context(question, targets=targets, current_stock_code=current_stock_code)
        analysis_summary = self._build_analysis_summary(stock_context, year=_extract_year(question))
        chart_context = self._build_chart_context(stock_context)
        evidence_items = self._collect_evidence(question, stock_context)

        cache_key = self._build_cache_key(question, stock_context, session_id=session_id, selected_mode=state.resolved_mode)
        source_signature = self._build_source_signature(analysis_summary, chart_context, evidence_items)
        cached = self._get_cached_result(cache_key, source_signature=source_signature)
        if cached is not None:
            state.answer = str(cached.get("answer") or "")
            state.suggestion = cached.get("suggestion")
            state.chart_desc = cached.get("chart_desc")
            state.report_markdown = cached.get("report_markdown")
            state.agent_mode = cached.get("agent_mode")
            state.framework = cached.get("framework") or self.framework
            state.summary = cached.get("summary") or state.summary
            state.resolved_mode = cached.get("selected_mode") or state.resolved_mode
            state.key_points = list(cached.get("key_points") or state.key_points or [])
            state.key_metrics = list(cached.get("key_metrics") or state.key_metrics or [])
            state.score_result = cached.get("score_result") or state.score_result
            state.chart_payload = list(cached.get("chart_payload") or state.chart_payload or [])
            state.evidence_list = list(cached.get("evidence_list") or state.evidence_list or [])
            state.follow_up_questions = list(cached.get("follow_up_questions") or state.follow_up_questions or [])
            state.preference_profile = cached.get("preference_profile") or state.preference_profile
            state.warnings = list(cached.get("warnings") or state.warnings or [])
            return state.to_agent_result()

        local_fallback = self._build_local_fallback(question, stock_context, analysis_summary, evidence_items, chart_context)
        if not self.llm_client.is_configured():
            payload = {
                **local_fallback,
                "framework": self.framework,
                "agent_mode": "kimi-config-missing",
            }
            state.answer = payload.get("answer")
            state.suggestion = payload.get("suggestion")
            state.chart_desc = payload.get("chart_desc")
            state.report_markdown = payload.get("report_markdown")
            state.agent_mode = payload.get("agent_mode")
            state.framework = payload.get("framework") or self.framework
            return state.to_agent_result()

        messages = build_chat_messages(
            user_question=question,
            stock_context=stock_context,
            analysis_summary=analysis_summary,
            chart_context=chart_context,
            evidence_items=evidence_items,
            history=history,
        )

        try:
            response_text = self.llm_client.chat(messages, temperature=1.0, max_tokens=DEFAULT_GLM_MAX_TOKENS)
            parsed = _extract_json_object(response_text) or {}
        except Exception as exc:
            llm_error_summary = _compact_text(str(exc), limit=220) or exc.__class__.__name__
            logger.warning("GLM minimal fallback: %s", llm_error_summary)
            parsed = {}

        payload = {
            "answer": str(parsed.get("answer") or local_fallback["answer"]).strip(),
            "suggestion": str(parsed.get("suggestion") or local_fallback["suggestion"]).strip(),
            "chart_desc": str(parsed.get("chart_desc") or local_fallback["chart_desc"]).strip(),
            "report_markdown": str(parsed.get("report_markdown") or local_fallback["report_markdown"]).strip(),
            "framework": self.framework,
            "agent_mode": self.agent_mode,
        }
        state.answer = payload.get("answer")
        state.suggestion = payload.get("suggestion")
        state.chart_desc = payload.get("chart_desc")
        state.report_markdown = payload.get("report_markdown")
        state.agent_mode = payload.get("agent_mode")
        state.framework = payload.get("framework") or self.framework
        result = state.to_agent_result()
        self._set_cached_result(
            cache_key,
            result=result,
            source_signature=source_signature,
            user_id=user_id or 1,
            query_text=question,
        )
        return result

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

    def _build_analysis_summary(self, stock_context: dict[str, Any] | None, *, year: int) -> dict[str, Any] | None:
        if not stock_context or not stock_context.get("stock_code"):
            return None

        with self.container.ctx.session() as db:
            result = self.analysis_service.diagnose(db, stock_context["stock_code"], year)
        if result is None:
            return None

        return {
            "stock_code": result.stock_code,
            "stock_name": result.stock_name,
            "year": result.year,
            "total_score": result.total_score,
            "level": result.level,
            "strengths": result.strengths[:3],
            "weaknesses": result.weaknesses[:3],
            "suggestion": result.suggestion,
            "dimensions": [
                {
                    "name": item.name,
                    "score": item.score,
                    "comment": item.comment,
                }
                for item in result.dimensions[:4]
            ],
        }

    def _build_chart_context(self, stock_context: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not stock_context or not stock_context.get("stock_code"):
            return []

        metrics = []
        with self.container.ctx.session() as db:
            for metric_name in ("营业总收入", "净利润"):
                try:
                    trend = self.analysis_service.get_metric_trend(db, stock_context["stock_code"], metric_name)
                except Exception:
                    continue
                points = trend.get("trend") or []
                if not points:
                    continue
                metrics.append(
                    {
                        "metric": metric_name,
                        "points": points[-3:],
                    }
                )
        return metrics

    def _collect_evidence(self, question: str, stock_context: dict[str, Any] | None) -> list[dict[str, Any]]:
        stock_code = stock_context.get("stock_code") if stock_context else None
        items: list[dict[str, Any]] = []
        search_plan = [
            ("announcement", self.container.retrieval.search_announcements, 2),
            ("financial_note", self.container.retrieval.search_financial_notes, 2),
            ("news", self.container.retrieval.search_news, 1),
        ]

        for doc_type, handler, limit in search_plan:
            result = handler(SearchRequest(query=question, stock_code=stock_code, top_k=limit))
            if not result.success or not result.data:
                continue
            for item in result.data.get("items") or []:
                compressed = self._compress_retrieval_item(item, default_kind=doc_type)
                if compressed:
                    items.append(compressed)

        items.extend(self._collect_temporary_report_evidence(question, stock_code=stock_code, limit=1))

        deduped: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for item in items:
            key = (str(item.get("kind") or ""), str(item.get("title") or ""), str(item.get("date") or ""))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
            if len(deduped) >= 6:
                break
        return deduped

    def _compress_retrieval_item(self, item: dict[str, Any], *, default_kind: str) -> dict[str, Any] | None:
        metadata = item.get("metadata") or {}
        source_record = item.get("source_record") or {}
        text = item.get("text") or ""
        title = metadata.get("title") or source_record.get("title") or source_record.get("note_type") or default_kind
        date = (
            metadata.get("publish_date")
            or metadata.get("date")
            or source_record.get("publish_date")
            or source_record.get("report_date")
            or source_record.get("publish_time")
            or ""
        )
        source = metadata.get("source_type") or source_record.get("source_type") or source_record.get("source_name") or default_kind
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

    def _collect_temporary_report_evidence(self, question: str, *, stock_code: str | None, limit: int) -> list[dict[str, Any]]:
        filters: dict[str, Any] = {"type": "research_report"}
        if stock_code:
            filters["stock_code"] = stock_code
        try:
            hits = get_store().search(question, top_k=limit, filters=filters)
        except Exception:
            return []

        items: list[dict[str, Any]] = []
        for hit in hits:
            meta = hit.get("meta") or {}
            items.append(
                {
                    "kind": "research_report",
                    "title": str(meta.get("title") or "研报"),
                    "date": str(meta.get("date") or ""),
                    "source": str(meta.get("source") or "research_report"),
                    "summary": _compact_text(hit.get("text") or "", limit=180),
                }
            )
        return items

    def _build_cache_key(
        self,
        question: str,
        stock_context: dict[str, Any] | None,
        *,
        session_id: int | None,
        selected_mode: str | None = None,
    ) -> str:
        stock_code = (stock_context or {}).get("stock_code") or "none"
        mode = selected_mode or "quick_query"
        digest = md5(f"{question}|{stock_code}|{session_id or 0}|{mode}".encode("utf-8")).hexdigest()[:16]
        return f"glm:min:{stock_code}:{digest}"

    def _build_source_signature(
        self,
        analysis_summary: dict[str, Any] | None,
        chart_context: list[dict[str, Any]],
        evidence_items: list[dict[str, Any]],
    ) -> str:
        raw = json.dumps(
            {
                "analysis": analysis_summary or {},
                "charts": chart_context,
                "evidence": evidence_items,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return md5(raw.encode("utf-8")).hexdigest()

    def _get_cached_result(self, cache_key: str, *, source_signature: str) -> dict[str, Any] | None:
        result = self.container.cache.get_query_cache(CacheQueryRequest(cache_key=cache_key))
        if not result.success or not result.data:
            return None
        if result.data.get("source_signature") != source_signature:
            return None
        cached = result.data.get("result_json")
        return cached if isinstance(cached, dict) else None

    def _set_cached_result(
        self,
        cache_key: str,
        *,
        result: dict[str, Any],
        source_signature: str,
        user_id: int,
        query_text: str,
    ) -> None:
        self.container.cache.set_query_cache(
            CacheSetQueryRequest(
                cache_key=cache_key,
                result=result,
                user_id=user_id,
                query_text=query_text,
                source_signature=source_signature,
                ttl_seconds=1800,
            )
        )

    def _build_local_fallback(
        self,
        question: str,
        stock_context: dict[str, Any] | None,
        analysis_summary: dict[str, Any] | None,
        evidence_items: list[dict[str, Any]],
        chart_context: list[dict[str, Any]],
    ) -> dict[str, str]:
        stock_name = (stock_context or {}).get("stock_name") or (stock_context or {}).get("stock_code") or "当前标的"
        if analysis_summary:
            answer = (
                f"{stock_name} 当前可用本地分析结果显示：综合评分 {analysis_summary.get('total_score', 'N/A')} 分，"
                f"评级 {analysis_summary.get('level', '未知')}。"
                f"重点建议：{analysis_summary.get('suggestion') or '建议结合公告、财报附注与新闻继续跟踪。'}"
            )
            suggestion = str(analysis_summary.get("suggestion") or "继续跟踪核心财务指标与公告催化。")
        else:
            evidence_text = evidence_items[0]["summary"] if evidence_items else "当前本地证据有限。"
            answer = f"关于“{question}”，当前已检索到的本地证据表明：{evidence_text}"
            suggestion = "建议补充更多结构化证据后再做结论判断。"

        if chart_context:
            first_chart = chart_context[0]
            chart_desc = f"建议展示 {first_chart.get('metric')} 最近 {len(first_chart.get('points') or [])} 期趋势，用于解释变化方向。"
        else:
            chart_desc = "建议优先展示综合评分、主要维度得分与关键证据时间线。"

        report_markdown = "\n".join(
            [
                f"# {stock_name} 最小分析草稿",
                f"## 一、财务健康度\n{answer}",
                f"## 二、成长潜力\n{chart_desc}",
                f"## 三、风险提示\n{_compact_text('；'.join(item['summary'] for item in evidence_items[:2]) or '当前证据不足，需继续跟踪公告与新闻。', limit=220)}",
                f"## 四、建议\n{suggestion}",
            ]
        )
        return {
            "answer": answer,
            "suggestion": suggestion,
            "chart_desc": chart_desc,
            "report_markdown": report_markdown,
        }


__all__ = ["GLMMinimalAgent"]