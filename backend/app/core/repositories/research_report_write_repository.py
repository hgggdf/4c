from __future__ import annotations

import hashlib

from app.core.database.models.research_report_hot import ResearchReportHot
from app.core.repositories.base import BaseRepository


def _ensure_uid(item: dict) -> dict:
    """确保研报记录带有 report_uid。

    未提供 UID 时，按范围、股票/行业、标题和发布日期生成 md5。
    """
    if not item.get("report_uid"):
        key = f"{item.get('scope_type','')}-{item.get('stock_code','')}-{item.get('industry_code','')}-{item.get('title','')}-{item.get('publish_date','')}"
        item = dict(item)
        item["report_uid"] = hashlib.md5(key.encode()).hexdigest()
    return item


class ResearchReportWriteRepository(BaseRepository):
    """研报写库入口。"""

    def batch_upsert_research_reports(self, items: list[dict]):
        """批量写入研报，按 report_uid 去重。"""
        items = [_ensure_uid(i) for i in items]
        return self.bulk_upsert(ResearchReportHot, items=items, unique_keys=["report_uid"])
