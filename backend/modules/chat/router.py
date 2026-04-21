"""聊天与 PDF 上传接口，负责问答请求分发和知识库补充。"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from core.database.session import get_db
from modules.chat.schemas import ChatRequest, ChatResponse
from modules.chat.service import ChatService

router = APIRouter(prefix="/api", tags=["chat"])
chat_service = ChatService()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """处理一轮聊天请求，并返回 LangChain 预留占位回复。"""
    return chat_service.handle_chat(db, request)


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
    db: Session = Depends(get_db)
):
    """获取用户聊天历史记录。"""
    return chat_service.get_chat_history(db, user_id, limit)
