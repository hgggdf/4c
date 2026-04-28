"""聊天业务服务。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from agent.integration.agent import LangChainAgentStub
from app.core.database.models.announcement_hot import AnnouncementHot
from app.core.database.models.company import CompanyMaster, CompanyProfile
from app.core.database.models.financial_hot import FinancialHot
from app.core.database.models.news_hot import NewsHot
from app.core.database.models.user import ChatMessage, ChatSession
from app.router.schemas.chat import ChatHistoryRecord, ChatRequest, ChatResponse

from .shared import build_quote_payload, ensure_demo_user, get_latest_trade_rows, resolve_company


class ChatService:
    """负责聊天占位响应与会话落库。"""

    def __init__(self) -> None:
        self.agent = LangChainAgentStub()

    def handle_chat(self, db: Session, request: ChatRequest) -> ChatResponse:
        user = ensure_demo_user(db, request.user_id)
        session = self._get_or_create_session(db, user.id, request.session_id, request.message)
        stock_code = self._resolve_stock_code(db, request) or session.current_stock_code

        if stock_code and session.current_stock_code != stock_code:
            session.current_stock_code = stock_code

        retrieval_trace = self._build_retrieval_trace(db, request, stock_code)
        data_sources = self._build_data_sources(retrieval_trace)
        source_notice = self._build_source_notice(data_sources)
        answer_prefix = self._build_answer_prefix(retrieval_trace, source_notice)

        db.add(ChatMessage(session_id=session.id, role="user", content=request.message, stock_code=stock_code, intent_type="langchain_pending"))
        db.flush()

        agent_result = self.agent.run(
            request.message,
            history=[item.model_dump() for item in request.history],
            targets=[item.model_dump() for item in request.targets],
            current_stock_code=session.current_stock_code,
            user_id=user.id,
            session_id=session.id,
            selected_mode=request.selected_mode,
            frontend_context=request.frontend_context,
            followup_from=request.followup_from,
            preference_hint=request.preference_hint,
        )

        answer = answer_prefix + agent_result["answer"]
        db.add(
            ChatMessage(
                session_id=session.id,
                role="assistant",
                content=answer,
                stock_code=stock_code,
                intent_type=agent_result.get("agent_mode") or "glm-5.1-minimal",
                tool_calls_json={
                    "framework": agent_result.get("framework"),
                    "agent_mode": agent_result.get("agent_mode"),
                    "suggestion": agent_result.get("suggestion"),
                    "chart_desc": agent_result.get("chart_desc"),
                    "report_markdown": agent_result.get("report_markdown"),
                    "retrieval_trace": retrieval_trace,
                    "data_sources": data_sources,
                    "source_notice": source_notice,
                },
            )
        )
        session.updated_at = datetime.now()
        db.flush()
        db.commit()

        quote = self._build_quote(db, stock_code) if stock_code else None
        return ChatResponse(
            answer=answer,
            suggestion=agent_result.get("suggestion"),
            chart_desc=agent_result.get("chart_desc"),
            report_markdown=agent_result.get("report_markdown"),
            quote=quote,
            session_id=session.id,
            agent_mode=agent_result.get("agent_mode"),
            summary=agent_result.get("summary"),
            selected_mode=agent_result.get("selected_mode") or request.selected_mode,
            key_points=agent_result.get("key_points") or [],
            key_metrics=agent_result.get("key_metrics") or [],
            score_result=agent_result.get("score_result"),
            chart_payload=agent_result.get("chart_payload") or [],
            evidence_list=agent_result.get("evidence_list") or [],
            follow_up_questions=agent_result.get("follow_up_questions") or [],
            preference_profile=agent_result.get("preference_profile"),
            warnings=agent_result.get("warnings") or [],
            retrieval_trace=retrieval_trace,
            data_sources=data_sources,
            source_notice=source_notice,
        )

    def get_chat_history(self, db: Session, user_id: int, limit: int = 20) -> dict:
        user = ensure_demo_user(db, user_id)
        sessions = list(db.execute(select(ChatSession).where(ChatSession.user_id == user.id).order_by(ChatSession.updated_at.desc(), ChatSession.id.desc()).limit(max(limit, 1))).scalars().all())
        if not sessions:
            return {"total": 0, "records": []}

        session_ids = [item.id for item in sessions]
        messages = list(db.execute(select(ChatMessage).where(ChatMessage.session_id.in_(session_ids)).order_by(ChatMessage.session_id.asc(), ChatMessage.created_at.asc(), ChatMessage.id.asc())).scalars().all())

        pending_questions: dict[int, ChatMessage] = {}
        records: list[ChatHistoryRecord] = []
        for message in messages:
            if message.role == "user":
                pending_questions[message.session_id] = message
                continue
            if message.role != "assistant":
                continue
            question = pending_questions.pop(message.session_id, None)
            if question is None:
                continue
            records.append(ChatHistoryRecord(id=message.id, question=question.content, answer=message.content, stock_code=message.stock_code or question.stock_code, create_time=message.created_at, session_id=message.session_id))

        records.sort(key=lambda item: item.create_time, reverse=True)
        return {"total": len(records), "records": [item.model_dump() for item in records[:limit]]}

    def _get_or_create_session(self, db: Session, user_id: int, session_id: int | None, message: str) -> ChatSession:
        if session_id is not None:
            existing = db.execute(select(ChatSession).where(ChatSession.id == session_id)).scalars().first()
            if existing is not None:
                return existing

        latest = db.execute(select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc(), ChatSession.id.desc()).limit(1)).scalars().first()
        if latest is not None:
            return latest

        title = (message or "新会话").strip()[:32] or "新会话"
        session = ChatSession(user_id=user_id, session_title=title)
        db.add(session)
        db.flush()
        return session

    def _resolve_stock_code(self, db: Session, request: ChatRequest) -> str | None:
        for target in request.targets:
            if target.type == "stock":
                company = resolve_company(db, target.symbol or target.name)
                if company is not None:
                    return company.stock_code

        company = resolve_company(db, request.message)
        return company.stock_code if company is not None else None

    def _build_retrieval_trace(self, db: Session, request: ChatRequest, stock_code: str | None) -> list[dict]:
        query = request.message.strip()
        if request.targets:
            query = f"{query} {' '.join(t.name for t in request.targets)}"
        if stock_code:
            query = f"{stock_code} {query}"

        items: list[dict] = []
        items.extend(self._keyword_search(db, query=query, stock_code=stock_code, top_k=3))
        items.extend(self._vector_search(db, query=query, stock_code=stock_code, top_k=3))
        items.sort(key=lambda item: item.get("final_score", 0), reverse=True)
        return items[:5]

    def _keyword_search(self, db: Session, *, query: str, stock_code: str | None, top_k: int) -> list[dict]:
        q = query.strip()
        if not q:
            return []
        lowered = q.lower()
        items: list[dict] = []

        anns = db.execute(select(AnnouncementHot).where(or_(AnnouncementHot.title.contains(q), AnnouncementHot.summary_text.contains(q), AnnouncementHot.content.contains(q))).order_by(AnnouncementHot.publish_date.desc(), AnnouncementHot.created_at.desc()).limit(top_k)).scalars().all()
        for row in anns:
            score = 1.5
            if stock_code and row.stock_code == stock_code:
                score += 0.8
            items.append({"doc_type": "announcement", "title": row.title, "snippet": row.summary_text or row.content or "", "match_source": "keyword", "keyword_score": score, "vector_score": None, "final_score": score})

        news_rows = db.execute(select(NewsHot).where(or_(NewsHot.title.contains(q), NewsHot.summary_text.contains(q), NewsHot.content.contains(q))).order_by(NewsHot.publish_time.desc(), NewsHot.created_at.desc()).limit(top_k)).scalars().all()
        for row in news_rows:
            score = 1.3
            codes = row.related_stock_codes_json
            if stock_code and isinstance(codes, str) and stock_code in codes:
                score += 0.6
            items.append({"doc_type": "news", "title": row.title, "snippet": row.summary_text or row.content or "", "match_source": "keyword", "keyword_score": score, "vector_score": None, "final_score": score})

        prof = db.execute(select(CompanyProfile, CompanyMaster.stock_name).join(CompanyMaster, CompanyMaster.stock_code == CompanyProfile.stock_code).where(or_(CompanyMaster.stock_name.contains(q), CompanyMaster.full_name.contains(q), CompanyProfile.business_summary.contains(q))).limit(top_k)).all()
        for profile, stock_name in prof:
            score = 1.7
            if stock_code and profile.stock_code == stock_code:
                score += 0.8
            items.append({"doc_type": "company_profile", "title": stock_name or profile.stock_code, "snippet": profile.business_summary or "", "match_source": "keyword", "keyword_score": score, "vector_score": None, "final_score": score})

        return items[:top_k]

    def _vector_search(self, db: Session, *, query: str, stock_code: str | None, top_k: int) -> list[dict]:
        if not stock_code:
            return []
        rows = db.execute(select(FinancialHot).where(FinancialHot.stock_code == stock_code).order_by(FinancialHot.report_date.desc()).limit(top_k)).scalars().all()
        items: list[dict] = []
        for row in rows:
            snippet = f"{getattr(row, 'revenue', '')} {getattr(row, 'net_profit', '')}"
            score = 0.9
            items.append({"doc_type": "financial", "title": f"{row.stock_code} 财务摘要", "snippet": snippet[:180], "match_source": "vector", "keyword_score": None, "vector_score": score, "final_score": score})
        return items[:top_k]

    def _build_data_sources(self, retrieval_trace: list[dict]) -> list[dict]:
        sources: list[dict] = []
        for item in retrieval_trace:
            sources.append({
                "data_type": item.get("doc_type"),
                "source": "local_database",
                "title": item.get("title"),
                "confidence": round(float(item.get("final_score") or 0), 2),
            })
        if sources:
            sources.append({
                "data_type": "fallback",
                "source": "external_api_training_data",
                "title": "本地数据库未覆盖的补充知识",
                "confidence": 0.0,
            })
        return sources

    def _build_source_notice(self, data_sources: list[dict]) -> str | None:
        if not data_sources:
            return None
        local_types = sorted({str(item.get("data_type") or "") for item in data_sources if item.get("source") == "local_database" and item.get("data_type")})
        if not local_types:
            return "本次回答使用了外部API训练数据补充，本地数据库未检索到足够证据。"
        if any(item.get("source") == "external_api_training_data" for item in data_sources):
            return f"本次回答主要依据本地数据库中的 {', '.join(local_types)} 数据；对本地未覆盖部分，使用了外部API训练数据补充。"
        return f"本次回答仅依据本地数据库中的 {', '.join(local_types)} 数据。"

    def _build_answer_prefix(self, retrieval_trace: list[dict], source_notice: str | None) -> str:
        lines = []
        if retrieval_trace:
            lines.append("我先基于本地检索结果做了初步定位：")
            for item in retrieval_trace[:3]:
                title = item.get("title") or "未命名"
                score = float(item.get("final_score") or 0)
                lines.append(f"- {title}（相关度 {score:.2f}）")
            lines.append("")
        if source_notice:
            lines.append(source_notice)
            lines.append("")
        return "\n".join(lines)

    def _build_quote(self, db: Session, stock_code: str):
        company = resolve_company(db, stock_code)
        if company is None:
            return None
        latest = get_latest_trade_rows(db, [company.stock_code]).get(company.stock_code)
        return build_quote_payload(company, latest)
