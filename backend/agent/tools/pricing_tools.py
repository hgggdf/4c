"""
Pricing reference search for rNPV parameter collection.

Queries the local knowledge base (announcements + research reports) using
the drug indication as the search query, then extracts price mentions from
the matched text to build a suggested price range for the user.
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Regex patterns for price extraction
# Matches patterns like: 3.8万元/年, 12万/年, 年费用约5万, ¥80,000, 8000元/月 etc.
_PRICE_PATTERNS = [
    # "X万元/年" or "X万/年"
    re.compile(r"(\d+(?:\.\d+)?)\s*万\s*(?:元|人民币)?\s*/?\s*(?:年|每年|per\s*year)", re.I),
    # "年治疗费用X万" or "年费用约X万"
    re.compile(r"(?:年治疗费|年费用|年均费用|年药费)[^\d]*(\d+(?:\.\d+)?)\s*万", re.I),
    # "定价X万" or "价格X万"
    re.compile(r"(?:定价|售价|价格|医保价|集采价)[^\d]*(\d+(?:\.\d+)?)\s*万", re.I),
    # "X元/年" → convert to wan
    re.compile(r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*元\s*/?\s*(?:年|每年)", re.I),
    # "X万元/月" → ×12
    re.compile(r"(\d+(?:\.\d+)?)\s*万\s*(?:元)?\s*/?\s*(?:月|每月)", re.I),
]

_WAN = 10_000


def _extract_prices_from_text(text: str) -> list[float]:
    """Extract price values (wan CNY / year) from a text chunk."""
    prices: list[float] = []
    text = text.replace(",", "")  # remove thousands separators

    # Pattern 0: X万/年
    for m in _PRICE_PATTERNS[0].finditer(text):
        v = float(m.group(1))
        if 0.1 <= v <= 500:
            prices.append(v)

    # Pattern 1: 年治疗费X万
    for m in _PRICE_PATTERNS[1].finditer(text):
        v = float(m.group(1))
        if 0.1 <= v <= 500:
            prices.append(v)

    # Pattern 2: 定价/集采价X万
    for m in _PRICE_PATTERNS[2].finditer(text):
        v = float(m.group(1))
        if 0.1 <= v <= 500:
            prices.append(v)

    # Pattern 3: X元/年 → convert
    for m in _PRICE_PATTERNS[3].finditer(text):
        v = float(m.group(1)) / _WAN
        if 0.1 <= v <= 500:
            prices.append(round(v, 2))

    # Pattern 4: X万/月 → ×12
    for m in _PRICE_PATTERNS[4].finditer(text):
        v = float(m.group(1)) * 12
        if 0.1 <= v <= 500:
            prices.append(round(v, 1))

    return prices


def search_pricing_reference(
    indication: str,
    *,
    top_k: int = 6,
) -> dict[str, Any]:
    """
    Search the local knowledge base for pricing mentions related to the indication.

    Returns:
        {
            "prices_wan": [list of extracted float values, wan CNY/year],
            "low": float | None,   # 25th-percentile suggestion
            "mid": float | None,   # median suggestion
            "high": float | None,  # 75th-percentile suggestion
            "suggestions": [str, str, str, str],  # chip labels for UI
            "sources": [{"title": ..., "date": ...}, ...],
        }
    """
    result: dict[str, Any] = {
        "prices_wan": [],
        "low": None,
        "mid": None,
        "high": None,
        "suggestions": ["1万元/年", "5万元/年", "20万元/年", "不知道，用行业基准"],
        "sources": [],
    }

    if not indication:
        return result

    try:
        from app.service.container import ServiceContainer
        from app.service.requests import SearchRequest

        container = ServiceContainer.build_default()
        query = f"{indication} 药品定价 年治疗费用 集采价 医保价"

        hits_result = container.retrieval.search_hybrid(
            SearchRequest(query=query, top_k=top_k)
        )
        if not hits_result.success or not hits_result.data:
            return result

        items = hits_result.data.get("items") or []
        all_prices: list[float] = []

        for item in items:
            text = item.get("text") or ""
            meta = item.get("metadata") or {}
            prices = _extract_prices_from_text(text)
            if prices:
                all_prices.extend(prices)
                result["sources"].append({
                    "title": meta.get("title") or "公告/研报",
                    "date": str(meta.get("publish_date") or meta.get("date") or ""),
                })

        if not all_prices:
            return result

        all_prices.sort()
        n = len(all_prices)
        result["prices_wan"] = all_prices
        result["low"] = round(all_prices[max(0, n // 4)], 1)
        result["mid"] = round(all_prices[n // 2], 1)
        result["high"] = round(all_prices[min(n - 1, (n * 3) // 4)], 1)

        # Build chip suggestions from extracted data
        chips: list[str] = []
        seen: set[float] = set()
        for v in [result["low"], result["mid"], result["high"]]:
            if v is not None and v not in seen:
                seen.add(v)
                chips.append(f"{v}万元/年（本地参考）")
        chips.append("不知道，用行业基准")
        result["suggestions"] = chips[:4]

        logger.info(
            "pricing_reference: indication=%r found %d prices, range=[%.1f, %.1f]",
            indication, n, all_prices[0], all_prices[-1],
        )

    except Exception as exc:
        logger.debug("search_pricing_reference failed: %s", exc)

    return result
