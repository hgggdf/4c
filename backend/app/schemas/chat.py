"""聊天相关接口的数据结构定义。"""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatHistoryItem(BaseModel):
    """单条对话历史消息。"""

    role: str = Field(..., description="user / assistant")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """聊天接口请求体。"""

    message: str = Field(..., min_length=1, description="用户提问")
    history: list[ChatHistoryItem] = Field(default_factory=list)
    user_id: int = Field(default=1, description="当前用户 ID")


class QuoteInfo(BaseModel):
    """聊天回答中附带的行情信息。"""

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
    """聊天接口响应体。"""

    answer: str
    quote: QuoteInfo | None = None


class ChatHistoryRecord(BaseModel):
    """聊天历史列表中的单条记录。"""

    id: int
    question: str
    answer: str
    stock_code: str | None = None
    create_time: datetime

    class Config:
        from_attributes = True
