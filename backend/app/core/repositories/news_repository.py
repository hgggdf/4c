from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.database.models.news_hot import NewsHot, NewsArchive
from app.core.repositories.base import BaseRepository


class NewsRepository(BaseRepository):
    @staticmethod
    def _since(days: int) -> datetime:
        return datetime.now() - timedelta(days=days)

    def list_news_raw(self, *, days: int = 30, news_type: str | None = None) -> list[NewsHot]:
        stmt = select(NewsHot).where(NewsHot.publish_time >= self._since(days))
        if news_type:
            stmt = stmt.where(NewsHot.news_type == news_type)
        return self.scalars_all(stmt.order_by(NewsHot.publish_time.desc()))

    def get_news_raw_by_id(self, news_id: int) -> NewsHot | None:
        return self.scalar_one_or_none(select(NewsHot).where(NewsHot.id == news_id))

    # 旧版 news_company_map → 按 related_stock_codes_json 过滤
    def list_news_by_company(self, stock_code: str, *, days: int = 30) -> list[NewsHot]:
        rows = self.scalars_all(
            select(NewsHot)
            .where(NewsHot.publish_time >= self._since(days))
            .order_by(NewsHot.publish_time.desc())
        )
        return [r for r in rows if _code_in_json(r.related_stock_codes_json, stock_code)]

    # 旧版 news_industry_map → 按 related_industry_codes_json 过滤
    def list_news_by_industry(self, industry_code: str, *, days: int = 30) -> list[NewsHot]:
        rows = self.scalars_all(
            select(NewsHot)
            .where(NewsHot.publish_time >= self._since(days))
            .order_by(NewsHot.publish_time.desc())
        )
        return [r for r in rows if _code_in_json(r.related_industry_codes_json, industry_code)]

    # 旧版 news_structured → 直接返回 news_hot（key_fields_json 含结构化字段）
    def list_news_structured(self, *, days: int = 30, topic_category: str | None = None) -> list[NewsHot]:
        return self.list_news_raw(days=days, news_type=topic_category)

    def list_company_impact_maps(self, stock_code: str, *, days: int = 30) -> list[NewsHot]:
        return self.list_news_by_company(stock_code, days=days)

    def list_industry_impact_maps(self, industry_code: str, *, days: int = 30) -> list[NewsHot]:
        return self.list_news_by_industry(industry_code, days=days)

    def list_industry_impact_events(self, industry_code: str, *, days: int = 30) -> list[NewsHot]:
        return self.list_news_by_industry(industry_code, days=days)


def _code_in_json(json_val, code: str) -> bool:
    if json_val is None:
        return False
    if isinstance(json_val, list):
        return code in json_val
    if isinstance(json_val, dict):
        return code in json_val.values() or code in json_val.keys()
    return False
