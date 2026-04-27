from __future__ import annotations

from sqlalchemy import or_, select

from app.core.database.models.research_report_hot import ResearchReportHot
from app.core.repositories.base import BaseRepository

# 旧 code → MED_* code 映射（双向）
_CODE_ALIASES: dict[str, list[str]] = {
    "medical_device":  ["MED_DEVICE"],
    "MED_DEVICE":      ["medical_device"],
    "biological":      ["MED_BIOLOGICAL"],
    "MED_BIOLOGICAL":  ["biological"],
    "pharma":          ["MED_MANUFACTURING"],
    "MED_MANUFACTURING": ["pharma"],
    "tcm":             ["MED_CHINESE_MEDICINE"],
    "MED_CHINESE_MEDICINE": ["tcm"],
    "healthcare":      ["MED_SERVICE"],
    "medical_service": ["MED_SERVICE"],
    "MED_SERVICE":     ["healthcare", "medical_service"],
    "pharma_trade":    ["MED_PHARMA_TRADE"],
    "MED_PHARMA_TRADE": ["pharma_trade"],
    "MED_RD":          ["pharma", "MED_MANUFACTURING"],
}

# 行业 code → 标题关键词列表（任意一个命中即匹配）
_INDUSTRY_KEYWORDS: dict[str, list[str]] = {
    "tcm":            ["中药", "中医", "中成药", "草药", "医药"],
    "biological":     ["生物", "疫苗", "抗体", "细胞治疗", "基因治疗", "CAR-T", "mRNA", "医药"],
    "pharma":         ["创新药", "化学药", "生物药", "原料药", "仿制药", "制药", "医药"],
    "chemical_drug":  ["化学制药", "化学药", "化药", "小分子", "原料药", "创新药", "医药"],
    "medical_device": ["医疗器械", "器械", "诊断", "影像", "手术机器人", "脑机接口", "眼科", "医疗设备"],
    "healthcare":     ["医疗服务", "医院", "诊所", "消费医疗", "医疗行业", "医疗"],
    "medical_service":["医疗服务", "医院", "诊所", "消费医疗", "医疗"],
    "pharma_trade":   ["医药商业", "药店", "药品流通", "医药流通", "医药"],
    "agri_chemical":  ["农药", "兽药", "农化"],
}


def _expand_codes(industry_code: str) -> list[str]:
    """返回该 code 及其所有别名，去重。"""
    codes = {industry_code}
    for alias in _CODE_ALIASES.get(industry_code, []):
        codes.add(alias)
    return list(codes)


class ResearchReportRepository(BaseRepository):
    def list_by_industry(self, industry_code: str, *, limit: int = 30) -> list[ResearchReportHot]:
        # 1. 按 industry_code 及其所有别名精确查
        if industry_code:
            codes = _expand_codes(industry_code)
            stmt = (
                select(ResearchReportHot)
                .where(ResearchReportHot.industry_code.in_(codes))
                .order_by(ResearchReportHot.publish_date.desc(), ResearchReportHot.created_at.desc())
                .limit(limit)
            )
            rows = self.scalars_all(stmt)
            if rows:
                return rows

        # 2. 用关键词对标题做模糊匹配
        keywords = _INDUSTRY_KEYWORDS.get(industry_code or "", [])
        if keywords:
            conditions = [ResearchReportHot.title.ilike(f"%{kw}%") for kw in keywords]
            stmt_kw = (
                select(ResearchReportHot)
                .where(
                    ResearchReportHot.scope_type == "industry",
                    or_(*conditions),
                )
                .order_by(ResearchReportHot.publish_date.desc(), ResearchReportHot.created_at.desc())
                .limit(limit)
            )
            rows = self.scalars_all(stmt_kw)
            if rows:
                return rows

        # 3. 兜底：返回所有行业研报
        stmt_fallback = (
            select(ResearchReportHot)
            .where(ResearchReportHot.scope_type == "industry")
            .order_by(ResearchReportHot.publish_date.desc(), ResearchReportHot.created_at.desc())
            .limit(limit)
        )
        return self.scalars_all(stmt_fallback)
