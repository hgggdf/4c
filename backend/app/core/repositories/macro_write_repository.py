from __future__ import annotations

from app.core.database.models.macro_hot import MacroIndicatorHot
from app.core.repositories.base import BaseRepository


class MacroWriteRepository(BaseRepository):
    def batch_upsert_macro_indicators(self, items: list[dict]):
        return self.bulk_upsert(MacroIndicatorHot, items=items, unique_keys=["indicator_name", "period"])
