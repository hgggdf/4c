from __future__ import annotations

from sqlalchemy import select

from app.core.database.models.research_report_hot import ResearchReportHot
from app.core.repositories.base import BaseRepository

# 旧 code → MED_* code 映射（双向）
_CODE_ALIASES: dict[str, list[str]] = {
    "medical_device":    ["MED_DEVICE"],
    "MED_DEVICE":        ["medical_device"],
    "biological":        ["MED_BIOLOGICAL"],
    "MED_BIOLOGICAL":    ["biological"],
    "pharma":            ["MED_MANUFACTURING"],
    "MED_MANUFACTURING": ["pharma"],
    "tcm":               ["MED_CHINESE_MEDICINE"],
    "MED_CHINESE_MEDICINE": ["tcm"],
    "healthcare":        ["MED_SERVICE"],
    "medical_service":   ["MED_SERVICE"],
    "MED_SERVICE":       ["healthcare", "medical_service"],
    "pharma_trade":      ["MED_PHARMA_TRADE"],
    "MED_PHARMA_TRADE":  ["pharma_trade"],
    "MED_RD":            ["pharma", "MED_MANUFACTURING", "MED_SERVICE"],
}


def _expand_codes(industry_code: str) -> list[str]:
    """展开 code 及其所有别名（递归，防止循环）。"""
    visited: set[str] = set()
    queue = [industry_code]
    while queue:
        code = queue.pop()
        if code in visited:
            continue
        visited.add(code)
        for alias in _CODE_ALIASES.get(code, []):
            if alias not in visited:
                queue.append(alias)
    return list(visited)


class ResearchReportRepository(BaseRepository):
    def list_by_industry(self, industry_code: str, *, limit: int = 30) -> list[ResearchReportHot]:
        if not industry_code:
            return []

        codes = _expand_codes(industry_code)

        # 1. 行业研报（scope_type='industry'）
        industry_rows = self.scalars_all(
            select(ResearchReportHot)
            .where(
                ResearchReportHot.scope_type == "industry",
                ResearchReportHot.industry_code.in_(codes),
            )
            .order_by(ResearchReportHot.publish_date.desc(), ResearchReportHot.created_at.desc())
            .limit(limit)
        )

        if len(industry_rows) >= limit:
            return industry_rows

        # 2. 用同行业公司研报补充，去重后凑满 limit
        seen_ids = {r.id for r in industry_rows}
        remaining = limit - len(industry_rows)
        company_rows = self.scalars_all(
            select(ResearchReportHot)
            .where(
                ResearchReportHot.scope_type == "company",
                ResearchReportHot.industry_code.in_(codes),
            )
            .order_by(ResearchReportHot.publish_date.desc(), ResearchReportHot.created_at.desc())
            .limit(remaining)
        )

        return industry_rows + [r for r in company_rows if r.id not in seen_ids]
