from __future__ import annotations

from sqlalchemy import select

from app.core.database.models.research_report_hot import ResearchReportHot, ResearchReportArchive
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
    # 行业代码有旧版 code 和 MED_* code 两套口径；查询前先扩展为等价代码集合。
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
    """研报读库入口。

    研报采用 research_report_hot + research_report_archive 双表结构。
    行业查询优先返回行业研报，不足时用同业公司研报补齐。
    """

    def list_by_industry(self, industry_code: str, *, limit: int = 30) -> list:
        """按行业代码查询研报。

        查询顺序：热库行业研报、冷库行业研报、热库公司研报、冷库公司研报。
        """
        if not industry_code:
            return []

        codes = _expand_codes(industry_code)

        # 1. 热库行业研报
        hot_industry = self.scalars_all(
            select(ResearchReportHot)
            .where(ResearchReportHot.scope_type == "industry", ResearchReportHot.industry_code.in_(codes))
            .order_by(ResearchReportHot.publish_date.desc(), ResearchReportHot.created_at.desc())
            .limit(limit)
        )

        if len(hot_industry) < limit:
            # 冷库行业研报补充
            remaining = limit - len(hot_industry)
            cold_industry = self.scalars_all(
                select(ResearchReportArchive)
                .where(ResearchReportArchive.scope_type == "industry", ResearchReportArchive.industry_code.in_(codes))
                .order_by(ResearchReportArchive.publish_date.desc(), ResearchReportArchive.created_at.desc())
                .limit(remaining)
            )
            industry_rows = hot_industry + cold_industry
        else:
            industry_rows = hot_industry

        if len(industry_rows) >= limit:
            self._increment_query_count(industry_rows)
            return industry_rows

        # 2. 热库公司研报补充
        seen_ids = {r.id for r in industry_rows}
        remaining = limit - len(industry_rows)
        hot_company = self.scalars_all(
            select(ResearchReportHot)
            .where(ResearchReportHot.scope_type == "company", ResearchReportHot.industry_code.in_(codes))
            .order_by(ResearchReportHot.publish_date.desc(), ResearchReportHot.created_at.desc())
            .limit(remaining)
        )
        company_rows = [r for r in hot_company if r.id not in seen_ids]

        if len(industry_rows) + len(company_rows) < limit:
            # 冷库公司研报补充
            remaining2 = limit - len(industry_rows) - len(company_rows)
            seen_ids.update(r.id for r in company_rows)
            cold_company = self.scalars_all(
                select(ResearchReportArchive)
                .where(ResearchReportArchive.scope_type == "company", ResearchReportArchive.industry_code.in_(codes))
                .order_by(ResearchReportArchive.publish_date.desc(), ResearchReportArchive.created_at.desc())
                .limit(remaining2)
            )
            company_rows += [r for r in cold_company if r.id not in seen_ids]

        all_rows = industry_rows + company_rows
        self._increment_query_count(all_rows)
        return all_rows
