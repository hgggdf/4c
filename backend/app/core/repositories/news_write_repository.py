from __future__ import annotations

import hashlib

from app.core.database.models.news_hot import NewsHot, NewsArchive
from app.core.repositories.base import BaseRepository


def _ensure_news_uid(item: dict) -> dict:
    if not item.get("news_uid"):
        key = f"{item.get('title','')}-{item.get('publish_time','')}-{item.get('source_name','')}"
        item = dict(item)
        item["news_uid"] = hashlib.md5(key.encode()).hexdigest()
    return item


class NewsWriteRepository(BaseRepository):
    def batch_upsert_news_raw(self, items: list[dict]):
        items = [_ensure_news_uid(i) for i in items]
        return self.bulk_upsert(NewsHot, items=items, unique_keys=["news_uid"])

    def batch_upsert_news(self, items: list[dict]):
        items = [_ensure_news_uid(i) for i in items]
        return self.bulk_upsert(NewsHot, items=items, unique_keys=["news_uid"])

    # 旧版 news_structured → 写入 news_hot，结构化字段存 key_fields_json
    def batch_upsert_news_structured(self, items: list[dict]):
        mapped = []
        for item in items:
            m = dict(item)
            m.setdefault("key_fields_json", {k: v for k, v in item.items()})
            mapped.append(_ensure_news_uid(m))
        return self.bulk_upsert(NewsHot, items=mapped, unique_keys=["news_uid"])

    # 旧版 news_industry_map → 更新 related_industry_codes_json
    def replace_news_industry_map(self, news_id: int, items: list[dict]):
        row = self.get_one_by(NewsHot, id=news_id)
        if row:
            row.related_industry_codes_json = [i.get("industry_code") for i in items if i.get("industry_code")]
            self.db.flush()
        return row

    # 旧版 news_company_map → 更新 related_stock_codes_json
    def replace_news_company_map(self, news_id: int, items: list[dict]):
        row = self.get_one_by(NewsHot, id=news_id)
        if row:
            row.related_stock_codes_json = [i.get("stock_code") for i in items if i.get("stock_code")]
            self.db.flush()
        return row

    # 旧版 industry_impact_events → 写入 news_hot，type 标记
    def batch_upsert_industry_impact_events(self, items: list[dict]):
        mapped = []
        for item in items:
            m = dict(item)
            m.setdefault("news_type", "industry_impact")
            m.setdefault("key_fields_json", {k: v for k, v in item.items()})
            mapped.append(m)
        return self.bulk_upsert(NewsHot, items=mapped, unique_keys=["news_uid"])

    def batch_delete_news_raw(self, items: list[dict]) -> list[int]:
        return self._batch_delete(NewsHot, items, ["news_uid"])

    def batch_delete_news_structured(self, items: list[dict]) -> list[int]:
        return self._batch_delete(NewsHot, items, ["news_uid"])

    def batch_delete_industry_impact_events(self, items: list[dict]) -> list[int]:
        return self._batch_delete(NewsHot, items, ["news_uid"])

    def _batch_delete(self, model, items: list[dict], key_fields: list[str]) -> list[int]:
        deleted_ids: list[int] = []
        for item in items:
            for row in self.list_by(model, **{k: item.get(k) for k in key_fields}):
                deleted_ids.append(row.id)
                self.delete(row, flush=False)
        if deleted_ids:
            self.db.flush()
        return deleted_ids
