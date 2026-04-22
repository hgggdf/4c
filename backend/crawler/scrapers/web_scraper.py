"""Crawler scraper facade with online strategies and fallback support."""

from __future__ import annotations

from crawler.clients.eastmoney_client import EastmoneyClient
from crawler.clients.exchange_client import ExchangeAnnouncementClient
from crawler.clients.http_client import CrawlerRuntimeConfig


def _runtime_config() -> CrawlerRuntimeConfig:
    return CrawlerRuntimeConfig.from_settings()


def fetch_eastmoney_industry_reports(
    keyword: str = "医药",
    limit: int = 5,
    *,
    source_mode: str = "auto",
    strategy: str = "auto",
) -> list[dict]:
    client = EastmoneyClient(config=_runtime_config())
    result = client.fetch_industry_reports(keyword=keyword, limit=limit, source_mode=source_mode, strategy=strategy)
    return result.get("items") or []


def fetch_eastmoney_stock_reports(
    symbol: str,
    limit: int = 3,
    *,
    source_mode: str = "auto",
    strategy: str = "auto",
) -> list[dict]:
    client = EastmoneyClient(config=_runtime_config())
    result = client.fetch_stock_reports(symbol, limit=limit, source_mode=source_mode, strategy=strategy)
    return result.get("items") or []


def fetch_sse_announcements(
    stock_code: str = "600276",
    limit: int = 5,
    *,
    source_mode: str = "auto",
    strategy: str = "auto",
) -> list[dict]:
    client = ExchangeAnnouncementClient(config=_runtime_config())
    result = client.fetch_announcements(stock_code, limit=limit, source_mode=source_mode, strategy=strategy)
    return [item for item in (result.get("items") or []) if item.get("exchange") == "SSE"]


def fetch_exchange_announcements(
    stock_code: str,
    limit: int = 10,
    *,
    source_mode: str = "auto",
    strategy: str = "auto",
) -> list[dict]:
    client = ExchangeAnnouncementClient(config=_runtime_config())
    result = client.fetch_announcements(stock_code, limit=limit, source_mode=source_mode, strategy=strategy)
    return result.get("items") or []


def fetch_pharma_news(
    symbol: str | None = None,
    *,
    source_mode: str = "auto",
    strategy: str = "auto",
) -> list[dict]:
    if symbol:
        return fetch_eastmoney_stock_reports(symbol, source_mode=source_mode, strategy=strategy)
    return fetch_eastmoney_industry_reports(keyword="医药", source_mode=source_mode, strategy=strategy)
