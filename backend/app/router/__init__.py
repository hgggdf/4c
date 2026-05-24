"""Router package exports.

Routers are loaded lazily so service modules can import router schemas without
triggering every API router during package initialization.
"""

from __future__ import annotations

from importlib import import_module

_ROUTER_EXPORTS = {
    "analysis_router": "analysis",
    "announcement_router": "announcement",
    "announcement_write_router": "announcement_write",
    "cache_router": "cache",
    "chat_router": "chat",
    "company_router": "company",
    "company_write_router": "company_write",
    "financial_router": "financial",
    "financial_write_router": "financial_write",
    "ingest_router": "ingest",
    "macro_router": "macro",
    "macro_write_router": "macro_write",
    "maintenance_router": "maintenance",
    "news_router": "news",
    "news_write_router": "news_write",
    "openclaw_ingest_router": "openclaw_ingest",
    "retrieval_router": "retrieval",
    "stock_router": "stock",
}

__all__ = list(_ROUTER_EXPORTS)


def __getattr__(name: str):
    module_name = _ROUTER_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    router = import_module(f"{__name__}.{module_name}").router
    globals()[name] = router
    return router
