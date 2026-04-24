"""证据组织工具 - 收集、去重、相关度排序医药分析证据。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvidenceItem:
    kind: str        # announcement / financial_note / news / research_report / clinical
    title: str
    date: str
    source: str
    summary: str
    relevance: float = 0.0   # 0-1
    tags: list[str] = field(default_factory=list)


@dataclass
class EvidenceBundle:
    stock_code: str
    stock_name: str
    query: str
    items: list[EvidenceItem] = field(default_factory=list)
    missing_types: list[str] = field(default_factory=list)


# 各类证据的基础权重（影响相关度初始分）
_KIND_BASE_WEIGHT: dict[str, float] = {
    "announcement":    0.9,
    "financial_note":  0.85,
    "clinical":        0.85,
    "research_report": 0.75,
    "news":            0.65,
    "unknown":         0.4,
}

# 关键词 → 标签映射，用于自动打标
_TAG_PATTERNS: list[tuple[str, str]] = [
    (r"创新药|NDA|IND|新药", "创新药"),
    (r"临床|I期|II期|III期|入组|受试者", "临床试验"),
    (r"集采|带量采购|中标|落标", "集采"),
    (r"医保|纳入|目录|谈判", "医保"),
    (r"审批|获批|上市|受理|CDE", "审批进展"),
    (r"处罚|警告|调查|违规|合规", "合规风险"),
    (r"研发|R&D|管线|pipeline", "研发"),
    (r"营收|收入|利润|毛利|净利", "财务"),
    (r"舆情|负面|正面|情感|评级", "舆情"),
]


def _calc_relevance(item: EvidenceItem, query: str) -> float:
    """基于关键词重叠计算 0-1 相关度。"""
    base = _KIND_BASE_WEIGHT.get(item.kind, 0.4)
    if not query:
        return base

    query_tokens = set(re.findall(r"[一-鿿]{2,}|[A-Za-z]{3,}", query))
    text = f"{item.title} {item.summary}"
    hit = sum(1 for t in query_tokens if t in text)
    boost = min(0.1 * hit, 0.2)   # 最多加0.2
    return min(1.0, base + boost)


def _extract_tags(item: EvidenceItem) -> list[str]:
    text = f"{item.title} {item.summary}"
    tags = []
    for pattern, tag in _TAG_PATTERNS:
        if re.search(pattern, text):
            tags.append(tag)
    return tags


class PharmaEvidenceCollector:
    """医药分析证据收集与组织器。"""

    _REQUIRED_KINDS = ["announcement", "financial_note", "news"]
    _MAX_ITEMS = 10

    def collect(
        self,
        query: str,
        stock_code: str,
        stock_name: str,
        raw_items: list[dict[str, Any]] | None = None,
    ) -> EvidenceBundle:
        """解析原始证据、打标、计算相关度、去重、排序，返回 EvidenceBundle。"""
        items = self._parse_raw(raw_items or [], query)
        items = self._deduplicate(items)
        items = sorted(items, key=lambda x: x.relevance, reverse=True)
        items = items[: self._MAX_ITEMS]
        missing = self._detect_missing(items)

        return EvidenceBundle(
            stock_code=stock_code,
            stock_name=stock_name,
            query=query,
            items=items,
            missing_types=missing,
        )

    # ── 内部方法 ─────────────────────────────────────────────────────────────

    def _parse_raw(self, raw_items: list[dict[str, Any]], query: str) -> list[EvidenceItem]:
        results = []
        for raw in raw_items:
            title = str(raw.get("title") or "").strip()
            summary = str(raw.get("summary") or "").strip()
            if not title and not summary:
                continue
            item = EvidenceItem(
                kind=str(raw.get("kind") or "unknown"),
                title=title,
                date=str(raw.get("date") or ""),
                source=str(raw.get("source") or ""),
                summary=summary,
            )
            item.relevance = _calc_relevance(item, query)
            item.tags = _extract_tags(item)
            results.append(item)
        return results

    def _deduplicate(self, items: list[EvidenceItem]) -> list[EvidenceItem]:
        """按 (kind, title) 去重，保留相关度最高的一条。"""
        seen: dict[tuple[str, str], EvidenceItem] = {}
        for item in items:
            key = (item.kind, item.title[:40])
            if key not in seen or item.relevance > seen[key].relevance:
                seen[key] = item
        return list(seen.values())

    def _detect_missing(self, items: list[EvidenceItem]) -> list[str]:
        present = {item.kind for item in items}
        return [k for k in self._REQUIRED_KINDS if k not in present]


__all__ = ["PharmaEvidenceCollector", "EvidenceBundle", "EvidenceItem"]
