"""
ingest_center / id_resolver.py
=============================

ID 反查模块。

职责：
    第3层 job 写入前，通过业务键反查第一层写入后的自增 ID。
    例如：
      - announcement 第3层 structured_announcements 需要 announcement_id
      - news 第3层 structured/maps/impact 需要 news_id / source_news_id

实现方式：
    通过 service_runtime.get_container() 获取 ServiceContainer，
    复用 container.ctx.session() 获取底层 SQLAlchemy session 直接查询。
"""

from __future__ import annotations

from typing import Optional

from app.core.database.models.announcement_hot import AnnouncementRawHot
from app.core.database.models.news_hot import NewsRawHot

from .service_runtime import get_container


def resolve_announcement_id(
    *,
    stock_code: str,
    title: str,
    publish_date: str,
) -> Optional[int]:
    """
    通过业务键反查 AnnouncementRawHot.id。

    查询条件与 ORM 唯一约束 uk_ann_raw_hot 对齐：
        (stock_code, title, publish_date)

    Args:
        stock_code: 股票代码。
        title: 公告标题。
        publish_date: 发布日期（YYYY-MM-DD）。

    Returns:
        announcement_id（自增主键），若未找到则返回 None。
    """
    container = get_container()
    with container.ctx.session() as db:
        row = (
            db.query(AnnouncementRawHot)
            .filter_by(stock_code=stock_code, title=title, publish_date=publish_date)
            .first()
        )
        return row.id if row else None


def resolve_news_id(
    *,
    news_uid: str,
) -> Optional[int]:
    """
    通过 news_uid 反查 NewsRawHot.id。

    查询条件与 ORM 唯一约束 uk_news_uid_hot 对齐：
        news_uid

    Args:
        news_uid: 新闻唯一标识。

    Returns:
        news_id（自增主键），若未找到则返回 None。
    """
    container = get_container()
    with container.ctx.session() as db:
        row = db.query(NewsRawHot).filter_by(news_uid=news_uid).first()
        return row.id if row else None
