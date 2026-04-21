from __future__ import annotations

from typing import Any

from app.core.database.models.financial_hot import (
    BalanceSheetHot,
    BusinessSegmentHot,
    CashflowStatementHot,
    FinancialMetricHot,
    FinancialNotesHot,
    IncomeStatementHot,
    StockDailyHot,
)
from app.core.repositories.base import BaseRepository


class FinancialWriteRepository(BaseRepository):
    def _batch_delete_by_keys(self, model: Any, items: list[dict], *, key_fields: list[str]) -> list[int]:
        deleted_ids: list[int] = []
        for item in items:
            filters = {key: item.get(key) for key in key_fields}
            rows = self.list_by(model, **filters)
            for row in rows:
                deleted_ids.append(row.id)
                self.delete(row, flush=False)
        if deleted_ids:
            self.db.flush()
        return deleted_ids

    def batch_upsert_income_statements(self, items: list[dict]):
        return self.bulk_upsert(IncomeStatementHot, items=items, unique_keys=["stock_code", "report_date", "report_type"])

    def batch_delete_income_statements(self, items: list[dict]) -> list[int]:
        return self._batch_delete_by_keys(IncomeStatementHot, items, key_fields=["stock_code", "report_date", "report_type"])

    def batch_upsert_balance_sheets(self, items: list[dict]):
        return self.bulk_upsert(BalanceSheetHot, items=items, unique_keys=["stock_code", "report_date", "report_type"])

    def batch_delete_balance_sheets(self, items: list[dict]) -> list[int]:
        return self._batch_delete_by_keys(BalanceSheetHot, items, key_fields=["stock_code", "report_date", "report_type"])

    def batch_upsert_cashflow_statements(self, items: list[dict]):
        return self.bulk_upsert(CashflowStatementHot, items=items, unique_keys=["stock_code", "report_date", "report_type"])

    def batch_delete_cashflow_statements(self, items: list[dict]) -> list[int]:
        return self._batch_delete_by_keys(CashflowStatementHot, items, key_fields=["stock_code", "report_date", "report_type"])

    def batch_upsert_financial_metrics(self, items: list[dict]):
        return self.bulk_upsert(FinancialMetricHot, items=items, unique_keys=["stock_code", "report_date", "metric_name"])

    def batch_delete_financial_metrics(self, items: list[dict]) -> list[int]:
        return self._batch_delete_by_keys(FinancialMetricHot, items, key_fields=["stock_code", "report_date", "metric_name"])

    def batch_upsert_financial_notes(self, items: list[dict]):
        return self.bulk_upsert(FinancialNotesHot, items=items, unique_keys=["stock_code", "report_date", "note_type"])

    def batch_delete_financial_notes(self, items: list[dict]) -> list[int]:
        return self._batch_delete_by_keys(FinancialNotesHot, items, key_fields=["stock_code", "report_date", "note_type"])

    def batch_upsert_business_segments(self, items: list[dict]):
        return self.bulk_upsert(BusinessSegmentHot, items=items, unique_keys=["stock_code", "report_date", "segment_name", "segment_type"])

    def batch_delete_business_segments(self, items: list[dict]) -> list[int]:
        return self._batch_delete_by_keys(BusinessSegmentHot, items, key_fields=["stock_code", "report_date", "segment_name", "segment_type"])

    def batch_upsert_stock_daily(self, items: list[dict]):
        return self.bulk_upsert(StockDailyHot, items=items, unique_keys=["stock_code", "trade_date"])

    def batch_delete_stock_daily(self, items: list[dict]) -> list[int]:
        return self._batch_delete_by_keys(StockDailyHot, items, key_fields=["stock_code", "trade_date"])
