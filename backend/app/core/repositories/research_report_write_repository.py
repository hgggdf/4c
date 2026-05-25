from __future__ import annotations

import hashlib

from app.core.database.models.research_report_hot import ResearchReportHot
from app.core.repositories.base import BaseRepository
from app.core.utils.dedup import prepare_dedup_record


def _ensure_uid(item: dict) -> dict:
    """确保研报记录带有 report_uid。

    未提供 UID 时，按范围、股票/行业、标题和发布日期生成 md5。
    """
    if not item.get("report_uid"):
        key = f"{item.get('scope_type','')}-{item.get('stock_code','')}-{item.get('industry_code','')}-{item.get('title','')}-{item.get('publish_date','')}"
        item = dict(item)
        item["report_uid"] = hashlib.md5(key.encode()).hexdigest()
    return item


def _prepare_research_report_item(item: dict) -> dict:
    return prepare_dedup_record("research_report", _ensure_uid(item))


class ResearchReportWriteRepository(BaseRepository):
    """研报写库入口。"""

    def batch_upsert_research_reports(self, items: list[dict]):
        """批量写入研报，按 report_uid 去重。"""
        items = [_prepare_research_report_item(i) for i in items]
        return self.bulk_upsert(
            ResearchReportHot,
            items=items,
            unique_keys=["dedup_key"],
            preserve_on_update=["report_uid"],
        )
