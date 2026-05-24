"""Backward-compatible entrypoint for the stock service."""

from app.service.stock_service import StockService

__all__ = ["StockService"]
