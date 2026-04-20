from __future__ import annotations

from core.database.models.news_hot import (
    IndustryImpactEventHot,
    NewsCompanyMapHot,
    NewsIndustryMapHot,
    NewsRawHot,
    NewsStructuredHot,
)
from core.repositories.base import BaseRepository


class NewsWriteRepository(BaseRepository):
    def batch_upsert_news_raw(self, items: list[dict]):
        return self.bulk_upsert(NewsRawHot, items=items, unique_keys=["news_uid"])

    def batch_upsert_news_structured(self, items: list[dict]):
        return self.bulk_upsert(NewsStructuredHot, items=items, unique_keys=["news_id", "topic_category"])

    def replace_news_industry_map(self, news_id: int, items: list[dict]):
        self.delete_where(NewsIndustryMapHot, news_id=news_id)
        return self.add_all([NewsIndustryMapHot(news_id=news_id, **item) for item in items])

    def replace_news_company_map(self, news_id: int, items: list[dict]):
        self.delete_where(NewsCompanyMapHot, news_id=news_id)
        return self.add_all([NewsCompanyMapHot(news_id=news_id, **item) for item in items])

    def batch_upsert_industry_impact_events(self, items: list[dict]):
        return self.bulk_upsert(IndustryImpactEventHot, items=items, unique_keys=["industry_code", "source_news_id", "event_date"])
