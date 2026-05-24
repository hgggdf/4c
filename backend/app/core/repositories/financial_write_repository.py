from __future__ import annotations

from app.core.database.models.financial_hot import FinancialHot, FinancialArchive
from app.core.repositories.base import BaseRepository


class FinancialWriteRepository(BaseRepository):
    def batch_upsert_income_statements(self, items: list[dict]):
        return self.bulk_upsert(FinancialHot, items=items, unique_keys=["stock_code", "report_date", "report_type"])

    def batch_upsert_balance_sheets(self, items: list[dict]):
        return self.bulk_upsert(FinancialHot, items=items, unique_keys=["stock_code", "report_date", "report_type"])

    def batch_upsert_cashflow_statements(self, items: list[dict]):
        return self.bulk_upsert(FinancialHot, items=items, unique_keys=["stock_code", "report_date", "report_type"])

    def batch_upsert_financial(self, items: list[dict]):
        return self.bulk_upsert(FinancialHot, items=items, unique_keys=["stock_code", "report_date", "report_type"])

    def batch_upsert_financial_metrics(self, items: list[dict]):
        return self.bulk_upsert(FinancialHot, items=items, unique_keys=["stock_code", "report_date", "report_type"])

    def batch_upsert_financial_notes(self, items: list[dict]):
        return self.bulk_upsert(FinancialHot, items=items, unique_keys=["stock_code", "report_date", "report_type"])

    def batch_upsert_business_segments(self, items: list[dict]):
        return self.bulk_upsert(FinancialHot, items=items, unique_keys=["stock_code", "report_date", "report_type"])

    def batch_upsert_stock_daily(self, items: list[dict]):
        # v3 无 stock_daily 表，静默忽略
        return [], 0, 0

    def batch_delete_income_statements(self, items: list[dict]) -> list[int]:
        return self._batch_delete(FinancialHot, items, ["stock_code", "report_date", "report_type"])

    def batch_delete_balance_sheets(self, items: list[dict]) -> list[int]:
        return self._batch_delete(FinancialHot, items, ["stock_code", "report_date", "report_type"])

    def batch_delete_cashflow_statements(self, items: list[dict]) -> list[int]:
        return self._batch_delete(FinancialHot, items, ["stock_code", "report_date", "report_type"])

    def batch_delete_financial_metrics(self, items: list[dict]) -> list[int]:
        return self._batch_delete(FinancialHot, items, ["stock_code", "report_date", "report_type"])

    def batch_delete_financial_notes(self, items: list[dict]) -> list[int]:
        return self._batch_delete(FinancialHot, items, ["stock_code", "report_date", "report_type"])

    def batch_delete_business_segments(self, items: list[dict]) -> list[int]:
        return self._batch_delete(FinancialHot, items, ["stock_code", "report_date", "report_type"])

    def batch_delete_stock_daily(self, items: list[dict]) -> list[int]:
        return []

    def _batch_delete(self, model, items: list[dict], key_fields: list[str]) -> list[int]:
        deleted_ids: list[int] = []
        for item in items:
            for row in self.list_by(model, **{k: item.get(k) for k in key_fields}):
                deleted_ids.append(row.id)
                self.delete(row, flush=False)
        if deleted_ids:
            self.db.flush()
        return deleted_ids
