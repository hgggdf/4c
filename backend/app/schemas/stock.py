"""股票行情、自选股与图表相关接口的数据结构定义。"""

from pydantic import BaseModel, Field


class QuoteResponse(BaseModel):
    """单只股票实时行情响应结构。"""

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


class KlinePoint(BaseModel):
    """单个交易日的 K 线点位。"""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class WatchItem(BaseModel):
    """用户自选股列表中的单条记录。"""

    symbol: str
    name: str


class WatchlistCreate(BaseModel):
    """新增自选股请求体。"""

    user_id: int = Field(default=1)
    symbol: str = Field(..., min_length=6, max_length=6)
    name: str | None = None
