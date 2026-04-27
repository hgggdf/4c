from __future__ import annotations

from sqlalchemy import select

from app.core.database.models.research_report_hot import ResearchReportHot
from app.core.repositories.base import BaseRepository


class ResearchReportRepository(BaseRepository):
    def list_by_industry(self, industry_code: str, *, limit: int = 30) -> list[ResearchReportHot]:
        stmt = (
            select(ResearchReportHot)
            .where(ResearchReportHot.industry_code == industry_code)
            .order_by(ResearchReportHot.publish_date.desc(), ResearchReportHot.created_at.desc())
            .limit(limit)
        )
        return self.scalars_all(stmt)
