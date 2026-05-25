from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.database.models.news_hot import NewsHot, NewsArchive
from app.core.repositories.base import BaseRepository


class NewsRepository(BaseRepository):
    """新闻读库入口。

    新闻采用 news_hot + news_archive 双表结构。
    公司/行业关联信息存储在 JSON 字段中，因此部分过滤在 Python 层完成。
    """

    @staticmethod
    def _since(days: int) -> datetime:
        """把最近 N 天转换成发布时间下限。"""
        return datetime.now() - timedelta(days=days)

    def list_news_raw(self, *, days: int = 30, news_type: str | None = None, limit: int | None = None) -> list[NewsHot | NewsArchive]:
        """按时间范围和新闻类型查询新闻列表。"""
        hot_stmt = select(NewsHot).where(NewsHot.publish_time >= self._since(days))
        cold_stmt = select(NewsArchive).where(NewsArchive.publish_time >= self._since(days))
        if news_type:
            hot_stmt = hot_stmt.where(NewsHot.news_type == news_type)
            cold_stmt = cold_stmt.where(NewsArchive.news_type == news_type)
        hot_stmt = hot_stmt.order_by(NewsHot.publish_time.desc())
        cold_stmt = cold_stmt.order_by(NewsArchive.publish_time.desc())
        return self._hot_cold_list(hot_stmt, cold_stmt, limit=limit)

    def get_news_raw_by_id(self, news_id: int) -> NewsHot | NewsArchive | None:
        """按新闻 id 查询详情，热库未命中时查冷库。"""
        return self._hot_cold_get(NewsHot, NewsArchive, news_id)

    def list_news_by_company(self, stock_code: str, *, days: int = 30) -> list[NewsHot | NewsArchive]:
        """查询与指定股票相关的新闻。

        related_stock_codes_json 是 JSON 字段，先按时间取候选，再在 Python 层判断是否包含代码。
        """
        hot_stmt = (select(NewsHot)
                    .where(NewsHot.publish_time >= self._since(days))
                    .order_by(NewsHot.publish_time.desc()))
        cold_stmt = (select(NewsArchive)
                     .where(NewsArchive.publish_time >= self._since(days))
                     .order_by(NewsArchive.publish_time.desc()))
        rows = self._hot_cold_list(hot_stmt, cold_stmt)
        return [r for r in rows if _code_in_json(r.related_stock_codes_json, stock_code)]

    def list_news_by_industry(self, industry_code: str, *, days: int = 30) -> list[NewsHot | NewsArchive]:
        """查询与指定行业相关的新闻。"""
        hot_stmt = (select(NewsHot)
                    .where(NewsHot.publish_time >= self._since(days))
                    .order_by(NewsHot.publish_time.desc()))
        cold_stmt = (select(NewsArchive)
                     .where(NewsArchive.publish_time >= self._since(days))
                     .order_by(NewsArchive.publish_time.desc()))
        rows = self._hot_cold_list(hot_stmt, cold_stmt)
        return [r for r in rows if _code_in_json(r.related_industry_codes_json, industry_code)]

    def list_news_structured(self, *, days: int = 30, topic_category: str | None = None) -> list[NewsHot | NewsArchive]:
        """结构化新闻兼容入口；topic_category 映射到 news_type。"""
        return self.list_news_raw(days=days, news_type=topic_category)

    def list_company_impact_maps(self, stock_code: str, *, days: int = 30) -> list[NewsHot | NewsArchive]:
        """公司影响映射兼容入口；v3 中直接返回公司相关新闻。"""
        return self.list_news_by_company(stock_code, days=days)

    def list_industry_impact_maps(self, industry_code: str, *, days: int = 30) -> list[NewsHot | NewsArchive]:
        """行业影响映射兼容入口；v3 中直接返回行业相关新闻。"""
        return self.list_news_by_industry(industry_code, days=days)

    def list_industry_impact_events(self, industry_code: str, *, days: int = 30) -> list[NewsHot | NewsArchive]:
        """行业影响事件兼容入口；v3 中直接返回行业相关新闻。"""
        return self.list_news_by_industry(industry_code, days=days)

    def list_butterfly_analyses(
        self,
        *,
        days: int = 90,
        event_type: str | None = None,
        severity: str | None = None,
        keyword: str | None = None,
        limit: int = 50,
    ) -> list[NewsHot | NewsArchive]:
        """查询蝴蝶效应分析新闻，并按解析字段做二次过滤。"""
        hot_stmt = (
            select(NewsHot)
            .where(NewsHot.news_type == "butterfly_analysis", NewsHot.publish_time >= self._since(days))
            .order_by(NewsHot.publish_time.desc())
            .limit(limit)
        )
        cold_stmt = (
            select(NewsArchive)
            .where(NewsArchive.news_type == "butterfly_analysis", NewsArchive.publish_time >= self._since(days))
            .order_by(NewsArchive.publish_time.desc())
        )
        rows = self._hot_cold_list(hot_stmt, cold_stmt, limit=limit)
        results = []
        for r in rows:
            kf = r.key_fields_json or {}
            ep = kf.get("event_parsed", {})
            if event_type and ep.get("event_type") != event_type:
                continue
            if severity and ep.get("severity") != severity:
                continue
            if keyword and keyword not in (kf.get("event_text") or ""):
                continue
            results.append(r)
        return results


def _code_in_json(json_val, code: str) -> bool:
    """判断 JSON 列表/字典中是否包含指定代码。"""
    if json_val is None:
        return False
    if isinstance(json_val, list):
        return code in json_val
    if isinstance(json_val, dict):
        return code in json_val.values() or code in json_val.keys()
    return False
