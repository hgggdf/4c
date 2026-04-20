from pydantic import BaseModel, Field


class QuoteResponse(BaseModel):
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
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class WatchItem(BaseModel):
    symbol: str
    name: str


class WatchlistCreate(BaseModel):
    user_id: int = Field(default=1)
    symbol: str = Field(..., min_length=6, max_length=6)
    name: str | None = None
