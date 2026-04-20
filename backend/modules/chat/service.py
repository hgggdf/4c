"""聊天业务服务，负责问答处理与聊天记录持久化。"""

from sqlalchemy.orm import Session

from agent.agent import StockAgent
from core.repositories.chat_repo import ChatRepository
from core.repositories.user_repo import UserRepository
from modules.chat.schemas import ChatHistoryRecord, ChatRequest, ChatResponse


class ChatService:
    """封装聊天主流程，连接智能体、用户仓储和聊天记录仓储。"""

    def __init__(self) -> None:
        self.agent = StockAgent()
        self.chat_repo = ChatRepository()
        self.user_repo = UserRepository()

    def handle_chat(self, db: Session, request: ChatRequest) -> ChatResponse:
        """处理一轮用户聊天请求，并把问答结果写入聊天历史表。"""
        user = self.user_repo.get_by_id(db, request.user_id)
        if user is None:
            user = self.user_repo.get_or_create_demo_user(db)

        result = self.agent.run(request.message, history=[h.model_dump() for h in request.history], db=db)
        self.chat_repo.create(
            db,
            user_id=user.id,
            question=request.message,
            answer=result["answer"],
            stock_code=result.get("symbol"),
        )
        return ChatResponse(answer=result["answer"], quote=result.get("quote"))

    def get_chat_history(self, db: Session, user_id: int, limit: int = 20) -> dict:
        """读取指定用户最近的聊天记录，并转换为接口响应结构。"""
        records = self.chat_repo.list_recent(db, user_id, limit)
        return {
            "total": len(records),
            "records": [ChatHistoryRecord.model_validate(record) for record in records],
        }
