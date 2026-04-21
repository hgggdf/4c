"""对外 API 模块共用的数据库辅助函数。"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.core.database.models as database_models
from app.core.database.models.company import CompanyMaster
from app.core.database.models.financial_hot import StockDailyHot
from config import get_settings


def to_float(value: Any, default: float | None = 0.0) -> float | None:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_percent(value: Any) -> float | None:
    number = to_float(value, None)
    if number is None:
        return None
    if -1.5 <= number <= 1.5:
        return number * 100
    return number


def extract_stock_code(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"(?<!\d)(\d{6})(?!\d)", text)
    return match.group(1) if match else None


def _flatten_aliases(raw: Any) -> list[str]:
    results: list[str] = []
    if raw is None:
        return results

    if isinstance(raw, dict):
        for key, value in raw.items():
            results.extend(_flatten_aliases(key))
            results.extend(_flatten_aliases(value))
        return results

    if isinstance(raw, (list, tuple, set)):
        for item in raw:
            results.extend(_flatten_aliases(item))
        return results

    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return results
        try:
            parsed = json.loads(text)
        except Exception:
            return [text]
        return _flatten_aliases(parsed)

    text = str(raw).strip()
    return [text] if text else results


def ensure_demo_user(db: Session, user_id: int | None = None) -> database_models.User:
    settings = get_settings()
    desired_id = int(user_id or settings.demo_user_id or 1)
    existing = db.execute(
        select(database_models.User).where(database_models.User.id == desired_id)
    ).scalars().first()
    if existing is not None:
        return existing

    username = settings.demo_username if desired_id == settings.demo_user_id else f"user_{desired_id}"
    occupied_name = db.execute(
        select(database_models.User).where(database_models.User.username == username)
    ).scalars().first()
    if occupied_name is not None and occupied_name.id != desired_id:
        username = f"{username}_{desired_id}"

    user = database_models.User(
        id=desired_id,
        username=username,
        password_hash="demo_password_hash",
        role="user",
        status="active",
    )
    db.add(user)
    db.flush()
    return user


def resolve_company(db: Session, query: str | None) -> CompanyMaster | None:
    text = (query or "").strip()
    if not text:
        return None

    stock_code = extract_stock_code(text)
    if stock_code:
        exact = db.execute(
            select(CompanyMaster).where(CompanyMaster.stock_code == stock_code)
        ).scalars().first()
        if exact is not None:
            return exact

    rows = list(
        db.execute(select(CompanyMaster).order_by(CompanyMaster.stock_code.asc())).scalars().all()
    )
    if not rows:
        return None

    lowered = text.lower()
    best: tuple[int, CompanyMaster] | None = None
    for row in rows:
        candidates = [
            row.stock_code,
            row.stock_name,
            row.full_name,
            *(_flatten_aliases(row.alias_json)),
        ]
        row_score = -1
        for candidate in candidates:
            candidate_text = str(candidate or "").strip()
            if not candidate_text:
                continue
            candidate_lower = candidate_text.lower()
            if candidate_lower == lowered:
                row_score = max(row_score, 1000 + len(candidate_lower))
            elif candidate_lower in lowered or lowered in candidate_lower:
                row_score = max(row_score, 100 + min(len(candidate_lower), len(lowered)))

        if row_score >= 0 and (best is None or row_score > best[0]):
            best = (row_score, row)

    return best[1] if best is not None else None


def get_latest_trade_rows(db: Session, stock_codes: list[str]) -> dict[str, StockDailyHot]:
    codes = [code for code in stock_codes if code]
    if not codes:
        return {}

    latest_subquery = (
        select(
            StockDailyHot.stock_code.label("stock_code"),
            func.max(StockDailyHot.trade_date).label("trade_date"),
        )
        .where(StockDailyHot.stock_code.in_(codes))
        .group_by(StockDailyHot.stock_code)
        .subquery()
    )

    rows = db.execute(
        select(StockDailyHot)
        .join(
            latest_subquery,
            (StockDailyHot.stock_code == latest_subquery.c.stock_code)
            & (StockDailyHot.trade_date == latest_subquery.c.trade_date),
        )
    ).scalars().all()
    return {row.stock_code: row for row in rows}


def build_quote_payload(company: CompanyMaster, trade_row: StockDailyHot | None) -> dict[str, Any]:
    if trade_row is None:
        return {
            "symbol": company.stock_code,
            "name": company.stock_name,
            "price": 0.0,
            "change": 0.0,
            "change_percent": 0.0,
            "change_pct": 0.0,
            "open": 0.0,
            "high": 0.0,
            "low": 0.0,
            "volume": "0",
            "time": "--",
        }

    open_price = to_float(trade_row.open_price, 0.0) or 0.0
    close_price = to_float(trade_row.close_price, 0.0) or 0.0
    change = close_price - open_price
    change_percent = (change / open_price * 100) if open_price else 0.0
    volume = trade_row.volume or 0
    time_label = trade_row.trade_date.isoformat() if trade_row.trade_date else "--"

    return {
        "symbol": company.stock_code,
        "name": company.stock_name,
        "price": round(close_price, 4),
        "change": round(change, 4),
        "change_percent": round(change_percent, 4),
        "change_pct": round(change_percent, 4),
        "open": round(open_price, 4),
        "high": round(to_float(trade_row.high_price, 0.0) or 0.0, 4),
        "low": round(to_float(trade_row.low_price, 0.0) or 0.0, 4),
        "volume": str(int(volume)),
        "time": time_label,
    }


def serialize_kline_row(row: StockDailyHot) -> dict[str, Any]:
    return {
        "date": row.trade_date.isoformat() if row.trade_date else "",
        "open": round(to_float(row.open_price, 0.0) or 0.0, 4),
        "high": round(to_float(row.high_price, 0.0) or 0.0, 4),
        "low": round(to_float(row.low_price, 0.0) or 0.0, 4),
        "close": round(to_float(row.close_price, 0.0) or 0.0, 4),
        "volume": float(row.volume or 0),
    }