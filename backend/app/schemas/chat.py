from datetime import datetime

from pydantic import BaseModel, Field


class ChatHistoryItem(BaseModel):
    role: str = Field(..., description="user / assistant")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户提问")
    history: list[ChatHistoryItem] = Field(default_factory=list)
    user_id: int = Field(default=1, description="当前用户 ID")


class QuoteInfo(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    open: float
    high: float
    low: float
    volume: str
    time: str


class ChatResponse(BaseModel):
    answer: str
    quote: QuoteInfo | None = None


class ChatHistoryRecord(BaseModel):
    id: int
    question: str
    answer: str
    stock_code: str | None = None
    create_time: datetime

    class Config:
        from_attributes = True
