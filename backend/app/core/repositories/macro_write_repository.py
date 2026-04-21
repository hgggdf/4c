from __future__ import annotations

from app.core.database.models.macro_hot import MacroIndicatorHot
from app.core.repositories.base import BaseRepository


class MacroWriteRepository(BaseRepository):
    def batch_upsert_macro_indicators(self, items: list[dict]):
        return self.bulk_upsert(MacroIndicatorHot, items=items, unique_keys=["indicator_name", "period"])

    def batch_delete_macro_indicators(self, items: list[dict]) -> list[int]:
        deleted_ids: list[int] = []
        for item in items:
            rows = self.list_by(MacroIndicatorHot, indicator_name=item.get("indicator_name"), period=item.get("period"))
            for row in rows:
                deleted_ids.append(row.id)
                self.delete(row, flush=False)
        if deleted_ids:
            self.db.flush()
        return deleted_ids
