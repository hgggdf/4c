from __future__ import annotations

import hashlib

from app.core.database.models.announcement_hot import AnnouncementHot, AnnouncementArchive
from app.core.repositories.base import BaseRepository


def _ensure_uid(item: dict) -> dict:
    if not item.get("announcement_uid"):
        key = f"{item.get('stock_code','')}-{item.get('title','')}-{item.get('publish_date','')}"
        item = dict(item)
        item["announcement_uid"] = hashlib.md5(key.encode()).hexdigest()
    return item


class AnnouncementWriteRepository(BaseRepository):
    def batch_upsert_raw_announcements(self, items: list[dict]):
        items = [_ensure_uid(i) for i in items]
        return self.bulk_upsert(AnnouncementHot, items=items, unique_keys=["stock_code", "title", "publish_date"])

    def batch_upsert_announcements(self, items: list[dict]):
        items = [_ensure_uid(i) for i in items]
        return self.bulk_upsert(AnnouncementHot, items=items, unique_keys=["announcement_uid"])

    # 旧版 structured → 写入 announcement_hot，category 存入 announcement_type
    def batch_upsert_structured_announcements(self, items: list[dict]):
        mapped = []
        for item in items:
            m = dict(item)
            if "category" in m and "announcement_type" not in m:
                m["announcement_type"] = m.pop("category")
            mapped.append(_ensure_uid(m))
        return self.bulk_upsert(AnnouncementHot, items=mapped, unique_keys=["stock_code", "title", "publish_date"])

    # 旧版事件扩展表 → 写入 announcement_hot，type 字段标记
    def batch_upsert_drug_approvals(self, items: list[dict]):
        return self._upsert_typed(items, "drug_approval")

    def batch_upsert_clinical_trials(self, items: list[dict]):
        return self._upsert_typed(items, "clinical_trial")

    def batch_upsert_procurement_events(self, items: list[dict]):
        return self._upsert_typed(items, "centralized_procurement")

    def batch_upsert_regulatory_risks(self, items: list[dict]):
        return self._upsert_typed(items, "regulatory_risk")

    def _upsert_typed(self, items: list[dict], ann_type: str):
        mapped = []
        for item in items:
            m = dict(item)
            m.setdefault("announcement_type", ann_type)
            m.setdefault("title", m.get("drug_name") or m.get("risk_type") or ann_type)
            m.setdefault("publish_date", m.get("approval_date") or m.get("event_date"))
            m.setdefault("key_fields_json", {k: v for k, v in item.items()})
            mapped.append(_ensure_uid(m))
        return self.bulk_upsert(AnnouncementHot, items=mapped, unique_keys=["stock_code", "title", "publish_date"])

    def batch_delete_raw_announcements(self, items: list[dict]) -> list[int]:
        return self._batch_delete(AnnouncementHot, items, ["stock_code", "title", "publish_date"])

    def batch_delete_structured_announcements(self, items: list[dict]) -> list[int]:
        return self._batch_delete(AnnouncementHot, items, ["stock_code", "title", "publish_date"])

    def batch_delete_drug_approvals(self, items: list[dict]) -> list[int]:
        return self._batch_delete(AnnouncementHot, items, ["stock_code", "title", "publish_date"])

    def batch_delete_clinical_trials(self, items: list[dict]) -> list[int]:
        return self._batch_delete(AnnouncementHot, items, ["stock_code", "title", "publish_date"])

    def batch_delete_procurement_events(self, items: list[dict]) -> list[int]:
        return self._batch_delete(AnnouncementHot, items, ["stock_code", "title", "publish_date"])

    def batch_delete_regulatory_risks(self, items: list[dict]) -> list[int]:
        return self._batch_delete(AnnouncementHot, items, ["stock_code", "title", "publish_date"])

    def _batch_delete(self, model, items: list[dict], key_fields: list[str]) -> list[int]:
        deleted_ids: list[int] = []
        for item in items:
            for row in self.list_by(model, **{k: item.get(k) for k in key_fields}):
                deleted_ids.append(row.id)
                self.delete(row, flush=False)
        if deleted_ids:
            self.db.flush()
        return deleted_ids
