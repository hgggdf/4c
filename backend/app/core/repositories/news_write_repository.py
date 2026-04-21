from __future__ import annotations

from typing import Any

from app.core.database.models.news_hot import (
    IndustryImpactEventHot,
    NewsCompanyMapHot,
    NewsIndustryMapHot,
    NewsRawHot,
    NewsStructuredHot,
)
from app.core.repositories.base import BaseRepository


class NewsWriteRepository(BaseRepository):
    def _batch_delete_by_keys(self, model: Any, items: list[dict], *, key_fields: list[str]) -> list[int]:
        deleted_ids: list[int] = []
        for item in items:
            filters = {key: item.get(key) for key in key_fields}
            rows = self.list_by(model, **filters)
            for row in rows:
                deleted_ids.append(row.id)
                self.delete(row, flush=False)
        if deleted_ids:
            self.db.flush()
        return deleted_ids

    def batch_upsert_news_raw(self, items: list[dict]):
        return self.bulk_upsert(NewsRawHot, items=items, unique_keys=["news_uid"])

    def batch_delete_news_raw(self, items: list[dict]) -> list[int]:
        return self._batch_delete_by_keys(NewsRawHot, items, key_fields=["news_uid"])

    def batch_upsert_news_structured(self, items: list[dict]):
        return self.bulk_upsert(NewsStructuredHot, items=items, unique_keys=["news_id", "topic_category"])

    def batch_delete_news_structured(self, items: list[dict]) -> list[int]:
        return self._batch_delete_by_keys(NewsStructuredHot, items, key_fields=["news_id", "topic_category"])

    def replace_news_industry_map(self, news_id: int, items: list[dict]):
        self.delete_where(NewsIndustryMapHot, news_id=news_id)
        return self.add_all([NewsIndustryMapHot(news_id=news_id, **item) for item in items])

    def replace_news_company_map(self, news_id: int, items: list[dict]):
        self.delete_where(NewsCompanyMapHot, news_id=news_id)
        return self.add_all([NewsCompanyMapHot(news_id=news_id, **item) for item in items])

    def batch_upsert_industry_impact_events(self, items: list[dict]):
        return self.bulk_upsert(IndustryImpactEventHot, items=items, unique_keys=["industry_code", "source_news_id", "event_date"])

    def batch_delete_industry_impact_events(self, items: list[dict]) -> list[int]:
        return self._batch_delete_by_keys(IndustryImpactEventHot, items, key_fields=["industry_code", "source_news_id", "event_date"])
