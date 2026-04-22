"""聊天路由正式 schema。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .common import BaseRequestModel


class ChatHistoryItem(BaseModel):
	"""单条对话历史消息。"""

	role: str = Field(..., description="user / assistant")
	content: str = Field(..., description="消息内容")


class ChatTarget(BaseModel):
	"""拖拽到聊天区的分析目标。"""

	symbol: str = Field(..., description="股票代码或行业标识")
	name: str = Field(..., description="展示名称")
	type: str = Field(default="stock", description="stock / industry")


class ChatRequest(BaseModel):
	"""聊天接口请求体。"""

	message: str = Field(..., min_length=1, description="用户提问")
	history: list[ChatHistoryItem] = Field(default_factory=list)
	user_id: int = Field(default=1, description="当前用户 ID")
	session_id: int | None = Field(default=None, description="会话 ID")
	targets: list[ChatTarget] = Field(default_factory=list, description="拖入的分析目标")


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
	suggestion: str | None = None
	chart_desc: str | None = None
	report_markdown: str | None = None
	quote: QuoteInfo | None = None
	session_id: int | None = None
	agent_mode: str | None = None


class ChatHistoryRecord(BaseModel):
	"""聊天历史列表中的单条记录。"""

	id: int
	question: str
	answer: str
	stock_code: str | None = None
	create_time: datetime
	session_id: int | None = None

	model_config = ConfigDict(from_attributes=True)


class ChatListSessionsModel(BaseRequestModel):
	user_id: int
	limit: int = 20


class ChatSessionModel(BaseRequestModel):
	session_id: int


class ChatCreateSessionModel(BaseRequestModel):
	user_id: int
	session_title: str | None = None


class ChatAppendMessageModel(BaseRequestModel):
	session_id: int
	content: str
	stock_code: str | None = None
	intent_type: str | None = None
	tool_calls: dict[str, Any] | None = None


class ChatUpdateCurrentStockModel(BaseRequestModel):
	session_id: int
	stock_code: str


__all__ = [
	"ChatHistoryItem",
	"ChatTarget",
	"ChatRequest",
	"QuoteInfo",
	"ChatResponse",
	"ChatHistoryRecord",
	"ChatListSessionsModel",
	"ChatSessionModel",
	"ChatCreateSessionModel",
	"ChatAppendMessageModel",
	"ChatUpdateCurrentStockModel",
]