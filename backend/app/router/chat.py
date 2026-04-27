"""正式聊天路由定义。"""

import json
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from agent.dialogue_agent import DialogueAgent
from app.core.database.session import get_db
from app.router.chat_service import ChatService as RuntimeChatService
from app.router.dependencies import get_container
from app.router.schemas.chat import (
	ChatAppendMessageModel,
	ChatCreateSessionModel,
	ChatDeleteSessionModel,
	ChatListSessionsModel,
	ChatRequest,
	ChatResponse,
	ChatSessionModel,
	ChatUpdateCurrentStockModel,
)

from app.router.utils import build_request, service_result_response
from app.service import ServiceContainer
from app.service.requests import (
	ChatAppendMessageRequest,
	ChatCreateSessionRequest,
	ChatListSessionsRequest,
	ChatSessionRequest,
	ChatUpdateCurrentStockRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])
chat_service = RuntimeChatService()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
	"""处理一轮聊天请求，并返回 LangChain 预留占位回复。"""
	return chat_service.handle_chat(db, request)


@router.post("/chat/stream")
def chat_stream(request: ChatRequest):
	"""Kimi 流式对话（SSE）。"""
	def event_generator():
		try:
			agent = DialogueAgent()
			for event in agent.chat_stream(
				request.message,
				history=[item.model_dump() for item in request.history],
				targets=[item.model_dump() for item in request.targets],
				current_stock_code=None,
				selected_mode=request.selected_mode,
				tool_autonomy=request.tool_autonomy,
			):
				if isinstance(event, dict):
					yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
				else:
					yield f"data: {json.dumps({'type': 'answer', 'content': str(event)}, ensure_ascii=False)}\n\n"
		except Exception as exc:
			logger.exception("chat_stream error")
			yield f"data: {json.dumps({'type': 'error', 'message': f'对话异常: {exc}'}, ensure_ascii=False)}\n\n"
		yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

	return StreamingResponse(
		event_generator(),
		media_type="text/event-stream",
		headers={
			"Cache-Control": "no-cache",
			"Connection": "keep-alive",
			"X-Accel-Buffering": "no",
		},
	)


@router.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
	"""PDF 入库功能暂未接入，将在后续 LangChain 工作流中统一设计。"""
	raise HTTPException(
		status_code=501,
		detail=f"PDF 入库暂未接入，文件 {file.filename} 已被拒绝。后续将并入 LangChain 工作流。",
	)


@router.get("/chat/history")
def get_chat_history(
	user_id: int = 1,
	limit: int = 20,
	db: Session = Depends(get_db),
):
	"""获取用户聊天历史记录。"""
	return chat_service.get_chat_history(db, user_id, limit)


@router.post("/chat/session")
def get_session(payload: ChatSessionModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.chat.get_session(build_request(ChatSessionRequest, payload)))


@router.post("/chat/sessions")
def list_sessions(payload: ChatListSessionsModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.chat.list_sessions(build_request(ChatListSessionsRequest, payload)))


@router.post("/chat/messages")
def list_messages(payload: ChatSessionModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.chat.list_messages(build_request(ChatSessionRequest, payload)))


@router.post("/chat/current-context")
def get_current_context(payload: ChatSessionModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.chat.get_current_context(build_request(ChatSessionRequest, payload)))


@router.post("/chat/create-session")
def create_session(payload: ChatCreateSessionModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.chat.create_session(build_request(ChatCreateSessionRequest, payload)))


@router.post("/chat/append-user-message")
def append_user_message(payload: ChatAppendMessageModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.chat.append_user_message(build_request(ChatAppendMessageRequest, payload)))


@router.post("/chat/append-assistant-message")
def append_assistant_message(payload: ChatAppendMessageModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.chat.append_assistant_message(build_request(ChatAppendMessageRequest, payload)))


@router.post("/chat/update-current-stock")
def update_current_stock(payload: ChatUpdateCurrentStockModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.chat.update_current_stock(build_request(ChatUpdateCurrentStockRequest, payload)))


@router.post("/chat/delete-session")
def delete_session(payload: ChatSessionModel, container: ServiceContainer = Depends(get_container)):
	return service_result_response(container.chat.delete_session(build_request(ChatSessionRequest, payload)))


__all__ = ["router"]
