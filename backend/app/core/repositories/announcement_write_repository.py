from __future__ import annotations

from app.core.database.models.announcement_hot import AnnouncementHot, AnnouncementArchive
from app.core.repositories.base import BaseRepository
from app.core.utils.convert import generate_uid_md5
from app.core.utils.dedup import prepare_dedup_record


def _ensure_uid(item: dict) -> dict:
    """确保公告记录带有 announcement_uid。

    未提供 UID 时，按 stock_code/title/publish_date 生成稳定 md5，作为兼容去重标识。
    """
    if not item.get("announcement_uid"):
        item = dict(item)
        item["announcement_uid"] = generate_uid_md5(item.get("stock_code"), item.get("title"), item.get("publish_date"))
    return item


def _prepare_announcement_item(item: dict) -> dict:
    return prepare_dedup_record("announcement", _ensure_uid(item))


class AnnouncementWriteRepository(BaseRepository):
    """公告写库入口。

    主要写入 announcement_hot。原始公告和结构化公告最终都落在同一张表里，
    通过 announcement_type/key_fields_json 保留事件类型和扩展字段。
    """

    def batch_upsert_raw_announcements(self, items: list[dict]):
        """批量写入原始公告，按 stock_code/title/publish_date 去重。"""
        items = [_prepare_announcement_item(i) for i in items]
        return self.bulk_upsert(
            AnnouncementHot,
            items=items,
            unique_keys=["dedup_key"],
            preserve_on_update=["announcement_uid"],
        )

    def batch_upsert_announcements(self, items: list[dict]):
        """按 announcement_uid 批量写入公告。"""
        items = [_prepare_announcement_item(i) for i in items]
        return self.bulk_upsert(
            AnnouncementHot,
            items=items,
            unique_keys=["dedup_key"],
            preserve_on_update=["announcement_uid"],
        )

    # 旧版 structured → 写入 announcement_hot，category 存入 announcement_type
    def batch_upsert_structured_announcements(self, items: list[dict]):
        """写入结构化公告；旧字段 category 会映射为 announcement_type。"""
        mapped = []
        for item in items:
            m = dict(item)
            if "category" in m and "announcement_type" not in m:
                m["announcement_type"] = m.pop("category")
            mapped.append(_prepare_announcement_item(m))
        return self.bulk_upsert(
            AnnouncementHot,
            items=mapped,
            unique_keys=["dedup_key"],
            preserve_on_update=["announcement_uid"],
        )

    # 旧版事件扩展表 → 写入 announcement_hot，type 字段标记
    def batch_upsert_drug_approvals(self, items: list[dict]):
        """写入药品获批事件，最终合并到 announcement_hot。"""
        return self._upsert_typed(items, "drug_approval")

    def batch_upsert_clinical_trials(self, items: list[dict]):
        """写入临床试验事件，最终合并到 announcement_hot。"""
        return self._upsert_typed(items, "clinical_trial")

    def batch_upsert_procurement_events(self, items: list[dict]):
        """写入集采事件，最终合并到 announcement_hot。"""
        return self._upsert_typed(items, "centralized_procurement")

    def batch_upsert_regulatory_risks(self, items: list[dict]):
        """写入监管风险事件，最终合并到 announcement_hot。"""
        return self._upsert_typed(items, "regulatory_risk")

    def _upsert_typed(self, items: list[dict], ann_type: str):
        """把旧版事件扩展表记录折叠成 announcement_hot 记录。"""
        mapped = []
        for item in items:
            m = dict(item)
            m.setdefault("announcement_type", ann_type)
            m.setdefault("title", m.get("drug_name") or m.get("risk_type") or ann_type)
            m.setdefault("publish_date", m.get("approval_date") or m.get("event_date"))
            m.setdefault("key_fields_json", {k: v for k, v in item.items()})
            mapped.append(_prepare_announcement_item(m))
        return self.bulk_upsert(
            AnnouncementHot,
            items=mapped,
            unique_keys=["dedup_key"],
            preserve_on_update=["announcement_uid"],
        )

    def batch_delete_raw_announcements(self, items: list[dict]) -> list[int]:
        """按 stock_code/title/publish_date 删除原始公告。"""
        return self._batch_delete(AnnouncementHot, items, ["stock_code", "title", "publish_date"])

    def batch_delete_structured_announcements(self, items: list[dict]) -> list[int]:
        """按 stock_code/title/publish_date 删除结构化公告。"""
        return self._batch_delete(AnnouncementHot, items, ["stock_code", "title", "publish_date"])

    def batch_delete_drug_approvals(self, items: list[dict]) -> list[int]:
        """删除药品获批事件兼容记录。"""
        return self._batch_delete(AnnouncementHot, items, ["stock_code", "title", "publish_date"])

    def batch_delete_clinical_trials(self, items: list[dict]) -> list[int]:
        """删除临床试验事件兼容记录。"""
        return self._batch_delete(AnnouncementHot, items, ["stock_code", "title", "publish_date"])

    def batch_delete_procurement_events(self, items: list[dict]) -> list[int]:
        """删除集采事件兼容记录。"""
        return self._batch_delete(AnnouncementHot, items, ["stock_code", "title", "publish_date"])

    def batch_delete_regulatory_risks(self, items: list[dict]) -> list[int]:
        """删除监管风险事件兼容记录。"""
        return self._batch_delete(AnnouncementHot, items, ["stock_code", "title", "publish_date"])

    def _batch_delete(self, model, items: list[dict], key_fields: list[str]) -> list[int]:
        """按给定字段逐条删除公告记录，返回删除 id。"""
        deleted_ids: list[int] = []
        for item in items:
            for row in self.list_by(model, **{k: item.get(k) for k in key_fields}):
                deleted_ids.append(row.id)
                self.delete(row, flush=False)
        if deleted_ids:
            self.db.flush()
        return deleted_ids
