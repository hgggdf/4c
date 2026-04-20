from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.database.models.news_hot import (
    IndustryImpactEventHot,
    NewsCompanyMapHot,
    NewsIndustryMapHot,
    NewsRawHot,
    NewsStructuredHot,
)
from core.repositories.base import BaseRepository


class NewsRepository(BaseRepository):
    @staticmethod
    def _since(days: int) -> datetime:
        return datetime.now() - timedelta(days=days)

    def list_news_raw(self, *, days: int = 30, news_type: str | None = None) -> list[NewsRawHot]:
        stmt = select(NewsRawHot).where(NewsRawHot.publish_time >= self._since(days))
        if news_type:
            stmt = stmt.where(NewsRawHot.news_type == news_type)
        stmt = stmt.order_by(NewsRawHot.publish_time.desc(), NewsRawHot.created_at.desc())
        return self.scalars_all(stmt)

    def get_news_raw_by_id(self, news_id: int) -> NewsRawHot | None:
        stmt = select(NewsRawHot).where(NewsRawHot.id == news_id).options(selectinload(NewsRawHot.structured_items), selectinload(NewsRawHot.company_maps), selectinload(NewsRawHot.industry_maps))
        return self.scalar_one_or_none(stmt)

    def list_news_by_company(self, stock_code: str, *, days: int = 30) -> list[tuple[NewsCompanyMapHot, NewsRawHot]]:
        stmt = select(NewsCompanyMapHot, NewsRawHot).join(NewsRawHot, NewsCompanyMapHot.news_id == NewsRawHot.id).where(NewsCompanyMapHot.stock_code == stock_code).where(NewsRawHot.publish_time >= self._since(days)).order_by(NewsRawHot.publish_time.desc(), NewsRawHot.created_at.desc())
        return list(self.db.execute(stmt).all())

    def list_news_by_industry(self, industry_code: str, *, days: int = 30) -> list[tuple[NewsIndustryMapHot, NewsRawHot]]:
        stmt = select(NewsIndustryMapHot, NewsRawHot).join(NewsRawHot, NewsIndustryMapHot.news_id == NewsRawHot.id).where(NewsIndustryMapHot.industry_code == industry_code).where(NewsRawHot.publish_time >= self._since(days)).order_by(NewsRawHot.publish_time.desc(), NewsRawHot.created_at.desc())
        return list(self.db.execute(stmt).all())

    def list_news_structured(self, *, days: int = 30, topic_category: str | None = None) -> list[NewsStructuredHot]:
        stmt = select(NewsStructuredHot).join(NewsRawHot, NewsStructuredHot.news_id == NewsRawHot.id).where(NewsRawHot.publish_time >= self._since(days))
        if topic_category:
            stmt = stmt.where(NewsStructuredHot.topic_category == topic_category)
        stmt = stmt.order_by(NewsRawHot.publish_time.desc(), NewsStructuredHot.created_at.desc())
        return self.scalars_all(stmt)

    def list_company_impact_maps(self, stock_code: str, *, days: int = 30) -> list[NewsCompanyMapHot]:
        stmt = select(NewsCompanyMapHot).join(NewsRawHot, NewsCompanyMapHot.news_id == NewsRawHot.id).where(NewsCompanyMapHot.stock_code == stock_code).where(NewsRawHot.publish_time >= self._since(days)).order_by(NewsRawHot.publish_time.desc())
        return self.scalars_all(stmt)

    def list_industry_impact_maps(self, industry_code: str, *, days: int = 30) -> list[NewsIndustryMapHot]:
        stmt = select(NewsIndustryMapHot).join(NewsRawHot, NewsIndustryMapHot.news_id == NewsRawHot.id).where(NewsIndustryMapHot.industry_code == industry_code).where(NewsRawHot.publish_time >= self._since(days)).order_by(NewsRawHot.publish_time.desc())
        return self.scalars_all(stmt)

    def list_industry_impact_events(self, industry_code: str, *, days: int = 30) -> list[IndustryImpactEventHot]:
        stmt = select(IndustryImpactEventHot).where(IndustryImpactEventHot.industry_code == industry_code)
        stmt = stmt.where(IndustryImpactEventHot.event_date >= self._since(days).date())
        stmt = stmt.order_by(IndustryImpactEventHot.event_date.desc(), IndustryImpactEventHot.created_at.desc())
        return self.scalars_all(stmt)
