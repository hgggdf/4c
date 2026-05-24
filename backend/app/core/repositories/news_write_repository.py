from __future__ import annotations

from app.core.database.models.news_hot import NewsHot, NewsArchive
from app.core.repositories.base import BaseRepository
from app.core.utils.convert import generate_uid_md5


def _ensure_news_uid(item: dict) -> dict:
    """确保新闻记录带有 news_uid。

    未提供 UID 时，按 title/publish_time/source_name 生成 md5，作为去重标识。
    """
    if not item.get("news_uid"):
        item = dict(item)
        item["news_uid"] = generate_uid_md5(item.get("title"), item.get("publish_time"), item.get("source_name"))
    return item


class NewsWriteRepository(BaseRepository):
    """新闻写库入口。

    v3 中原始新闻、结构化新闻、行业影响事件都写入 news_hot，
    关联公司/行业以 JSON 字段保存。
    """

    def batch_upsert_news_raw(self, items: list[dict]):
        """批量写入原始新闻，按 news_uid 去重。"""
        items = [_ensure_news_uid(i) for i in items]
        return self.bulk_upsert(NewsHot, items=items, unique_keys=["news_uid"])

    def batch_upsert_news(self, items: list[dict]):
        """通用新闻写入入口，按 news_uid 去重。"""
        items = [_ensure_news_uid(i) for i in items]
        return self.bulk_upsert(NewsHot, items=items, unique_keys=["news_uid"])

    # 旧版 news_structured → 写入 news_hot，结构化字段存 key_fields_json
    def batch_upsert_news_structured(self, items: list[dict]):
        """写入结构化新闻；原始结构化字段保存在 key_fields_json。"""
        mapped = []
        for item in items:
            m = dict(item)
            m.setdefault("key_fields_json", {k: v for k, v in item.items()})
            mapped.append(_ensure_news_uid(m))
        return self.bulk_upsert(NewsHot, items=mapped, unique_keys=["news_uid"])

    # 旧版 news_industry_map → 更新 related_industry_codes_json
    def replace_news_industry_map(self, news_id: int, items: list[dict]):
        """替换指定新闻关联的行业代码列表。"""
        row = self.get_one_by(NewsHot, id=news_id)
        if row:
            row.related_industry_codes_json = [i.get("industry_code") for i in items if i.get("industry_code")]
            self.db.flush()
        return row

    # 旧版 news_company_map → 更新 related_stock_codes_json
    def replace_news_company_map(self, news_id: int, items: list[dict]):
        """替换指定新闻关联的股票代码列表。"""
        row = self.get_one_by(NewsHot, id=news_id)
        if row:
            row.related_stock_codes_json = [i.get("stock_code") for i in items if i.get("stock_code")]
            self.db.flush()
        return row

    # 旧版 industry_impact_events → 写入 news_hot，type 标记
    def batch_upsert_industry_impact_events(self, items: list[dict]):
        """写入行业影响事件；v3 中折叠为 news_type=industry_impact 的新闻。"""
        mapped = []
        for item in items:
            m = dict(item)
            m.setdefault("news_type", "industry_impact")
            m.setdefault("key_fields_json", {k: v for k, v in item.items()})
            mapped.append(m)
        return self.bulk_upsert(NewsHot, items=mapped, unique_keys=["news_uid"])

    def batch_delete_news_raw(self, items: list[dict]) -> list[int]:
        """按 news_uid 删除原始新闻。"""
        return self._batch_delete(NewsHot, items, ["news_uid"])

    def batch_delete_news_structured(self, items: list[dict]) -> list[int]:
        """按 news_uid 删除结构化新闻。"""
        return self._batch_delete(NewsHot, items, ["news_uid"])

    def batch_delete_industry_impact_events(self, items: list[dict]) -> list[int]:
        """按 news_uid 删除行业影响事件兼容记录。"""
        return self._batch_delete(NewsHot, items, ["news_uid"])

    def _batch_delete(self, model, items: list[dict], key_fields: list[str]) -> list[int]:
        """按给定字段逐条删除新闻记录，返回删除 id。"""
        deleted_ids: list[int] = []
        for item in items:
            for row in self.list_by(model, **{k: item.get(k) for k in key_fields}):
                deleted_ids.append(row.id)
                self.delete(row, flush=False)
        if deleted_ids:
            self.db.flush()
        return deleted_ids
