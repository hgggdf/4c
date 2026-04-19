from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from database.session import get_db
from schemas.chat import ChatRequest, ChatResponse
from service.chat_service import ChatService
from data.pdf_parser import extract_text_from_pdf_bytes, summarize_annual_report
from data.knowledge_store import get_store

router = APIRouter(prefix="/api", tags=["chat"])
chat_service = ChatService()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    return chat_service.handle_chat(db, request)


@router.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """上传 PDF 年报/研报，自动解析并存入知识库"""
    try:
        content = await file.read()
        text = extract_text_from_pdf_bytes(content, max_pages=30)
        summary = summarize_annual_report(text, max_chars=2000)

        store = get_store()
        store.add(summary, meta={"source": file.filename, "type": "pdf"})

        return {
            "status": "ok",
            "filename": file.filename,
            "text_length": len(text),
            "summary_length": len(summary),
            "message": "PDF 已解析并存入知识库，可以开始提问了"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/chat/history")
def get_chat_history(
    user_id: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取用户聊天历史记录"""
    from repository.chat_repo import ChatRepository
    from schemas.chat import ChatHistoryRecord

    repo = ChatRepository()
    records = repo.list_recent(db, user_id, limit)

    return {
        "total": len(records),
        "records": [ChatHistoryRecord.model_validate(r) for r in records]
    }
