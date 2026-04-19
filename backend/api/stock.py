from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.session import get_db
from schemas.stock import KlinePoint, QuoteResponse, WatchItem, WatchlistCreate
from service.stock_service import StockService

router = APIRouter(prefix="/api/stock", tags=["stock"])
stock_service = StockService()


@router.get("/quote", response_model=QuoteResponse)
def get_quote(symbol: str = Query(..., description="股票代码")):
    return stock_service.get_quote(symbol)


@router.get("/kline", response_model=list[KlinePoint])
def get_kline(
    symbol: str = Query(..., description="股票代码"),
    days: int = Query(30, ge=5, le=120, description="近N日数据"),
    db: Session = Depends(get_db),
):
    return stock_service.get_kline(db, symbol, days)


@router.get("/watchlist", response_model=list[WatchItem])
def get_watchlist(
    user_id: int = Query(1, description="用户 ID"),
    db: Session = Depends(get_db),
):
    return stock_service.get_watchlist(db, user_id)


@router.post("/watchlist", response_model=WatchItem)
def add_watchlist(payload: WatchlistCreate, db: Session = Depends(get_db)):
    return stock_service.add_watchlist(db, payload.user_id, payload.symbol, payload.name)


@router.delete("/watchlist")
def delete_watchlist(
    user_id: int = Query(1),
    symbol: str = Query(...),
    db: Session = Depends(get_db),
):
    return stock_service.remove_watchlist(db, user_id, symbol)
