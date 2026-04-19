from sqlalchemy.orm import Session

from agent.agent import StockAgent
from repository.chat_repo import ChatRepository
from repository.user_repo import UserRepository
from schemas.chat import ChatRequest, ChatResponse


class ChatService:
    def __init__(self) -> None:
        self.agent = StockAgent()
        self.chat_repo = ChatRepository()
        self.user_repo = UserRepository()

    def handle_chat(self, db: Session, request: ChatRequest) -> ChatResponse:
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
