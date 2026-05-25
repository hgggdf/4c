from __future__ import annotations

from app.core.database.models.macro_hot import MacroIndicator
from app.core.repositories.base import BaseRepository


class MacroWriteRepository(BaseRepository):
    """宏观指标写库入口。"""

    def batch_upsert_macro_indicators(self, items: list[dict]):
        """批量写入宏观指标，按 indicator_name + period 去重。"""
        return self.bulk_upsert(MacroIndicator, items=items, unique_keys=["indicator_name", "period"])

    def batch_delete_macro_indicators(self, items: list[dict]) -> list[int]:
        """按 indicator_name + period 批量删除宏观指标。"""
        deleted_ids: list[int] = []
        for item in items:
            for row in self.list_by(MacroIndicator,
                                    indicator_name=item.get("indicator_name"),
                                    period=item.get("period")):
                deleted_ids.append(row.id)
                self.delete(row, flush=False)
        if deleted_ids:
            self.db.flush()
        return deleted_ids
