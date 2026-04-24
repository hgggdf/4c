"""聊天业务服务。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from agent.integration.agent import LangChainAgentStub
from app.core.database.models.user import ChatMessage, ChatSession
from app.router.schemas.chat import ChatHistoryRecord, ChatRequest, ChatResponse

from .shared import build_quote_payload, ensure_demo_user, get_latest_trade_rows, resolve_company


class ChatService:
    """负责聊天占位响应与会话落库。"""

    def __init__(self) -> None:
        self.agent = LangChainAgentStub()

    def handle_chat(self, db: Session, request: ChatRequest) -> ChatResponse:
        """处理一轮聊天请求，并把用户消息与占位回复写入聊天会话。"""
        user = ensure_demo_user(db, request.user_id)
        session = self._get_or_create_session(db, user.id, request.session_id, request.message)
        stock_code = self._resolve_stock_code(db, request)
        if not stock_code:
            stock_code = session.current_stock_code

        if stock_code and session.current_stock_code != stock_code:
            session.current_stock_code = stock_code

        db.add(
            ChatMessage(
                session_id=session.id,
                role="user",
                content=request.message,
                stock_code=stock_code,
                intent_type="langchain_pending",
            )
        )
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

        db.add(
            ChatMessage(
                session_id=session.id,
                role="assistant",
                content=agent_result["answer"],
                stock_code=stock_code,
                intent_type=agent_result.get("agent_mode") or "glm-5.1-minimal",
                tool_calls_json={
                    "framework": agent_result.get("framework"),
                    "agent_mode": agent_result.get("agent_mode"),
                    "suggestion": agent_result.get("suggestion"),
                    "chart_desc": agent_result.get("chart_desc"),
                    "report_markdown": agent_result.get("report_markdown"),
                },
            )
        )
        session.updated_at = datetime.now()
        db.flush()
        db.commit()

        quote = self._build_quote(db, stock_code) if stock_code else None
        return ChatResponse(
            answer=agent_result["answer"],
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
        )

    def get_chat_history(self, db: Session, user_id: int, limit: int = 20) -> dict:
        """读取用户最近的问答对。"""
        user = ensure_demo_user(db, user_id)
        sessions = list(
            db.execute(
                select(ChatSession)
                .where(ChatSession.user_id == user.id)
                .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
                .limit(max(limit, 1))
            ).scalars().all()
        )
        if not sessions:
            return {"total": 0, "records": []}

        session_ids = [item.id for item in sessions]
        messages = list(
            db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id.in_(session_ids))
                .order_by(ChatMessage.session_id.asc(), ChatMessage.created_at.asc(), ChatMessage.id.asc())
            ).scalars().all()
        )

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

            records.append(
                ChatHistoryRecord(
                    id=message.id,
                    question=question.content,
                    answer=message.content,
                    stock_code=message.stock_code or question.stock_code,
                    create_time=message.created_at,
                    session_id=message.session_id,
                )
            )

        records.sort(key=lambda item: item.create_time, reverse=True)
        return {
            "total": len(records),
            "records": [item.model_dump() for item in records[:limit]],
        }

    def _get_or_create_session(
        self,
        db: Session,
        user_id: int,
        session_id: int | None,
        message: str,
    ) -> ChatSession:
        if session_id is not None:
            existing = db.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            ).scalars().first()
            if existing is not None:
                return existing

        latest = db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
            .limit(1)
        ).scalars().first()
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

    def _build_quote(self, db: Session, stock_code: str):
        company = resolve_company(db, stock_code)
        if company is None:
            return None
        latest = get_latest_trade_rows(db, [company.stock_code]).get(company.stock_code)
        return build_quote_payload(company, latest)