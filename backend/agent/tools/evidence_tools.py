"""证据组织工具骨架 - 收集并结构化医药分析证据。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvidenceItem:
    kind: str        # announcement / financial_note / news / research_report / clinical
    title: str
    date: str
    source: str
    summary: str
    relevance: float = 0.0  # 0-1 相关度
    tags: list[str] = field(default_factory=list)


@dataclass
class EvidenceBundle:
    stock_code: str
    stock_name: str
    query: str
    items: list[EvidenceItem] = field(default_factory=list)
    missing_types: list[str] = field(default_factory=list)


class PharmaEvidenceCollector:
    """医药分析证据收集与组织器。"""

    _REQUIRED_KINDS = ["announcement", "financial_note", "news"]

    def collect(
        self,
        query: str,
        stock_code: str,
        stock_name: str,
        raw_items: list[dict[str, Any]] | None = None,
    ) -> EvidenceBundle:
        """从原始检索结果中组织证据，返回 EvidenceBundle。"""
        # TODO: M3阶段实现真实收集与相关度排序逻辑
        items = self._parse_raw(raw_items or [])
        missing = self._detect_missing(items)
        return EvidenceBundle(
            stock_code=stock_code,
            stock_name=stock_name,
            query=query,
            items=items,
            missing_types=missing,
        )

    def _parse_raw(self, raw_items: list[dict[str, Any]]) -> list[EvidenceItem]:
        results = []
        for item in raw_items:
            results.append(
                EvidenceItem(
                    kind=str(item.get("kind") or "unknown"),
                    title=str(item.get("title") or ""),
                    date=str(item.get("date") or ""),
                    source=str(item.get("source") or ""),
                    summary=str(item.get("summary") or ""),
                )
            )
        return results

    def _detect_missing(self, items: list[EvidenceItem]) -> list[str]:
        present = {item.kind for item in items}
        return [k for k in self._REQUIRED_KINDS if k not in present]


__all__ = ["PharmaEvidenceCollector", "EvidenceBundle", "EvidenceItem"]
