from __future__ import annotations

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
    def batch_upsert_income_statements(self, items: list[dict]):
        return self.bulk_upsert(IncomeStatementHot, items=items, unique_keys=["stock_code", "report_date", "report_type"])

    def batch_upsert_balance_sheets(self, items: list[dict]):
        return self.bulk_upsert(BalanceSheetHot, items=items, unique_keys=["stock_code", "report_date", "report_type"])

    def batch_upsert_cashflow_statements(self, items: list[dict]):
        return self.bulk_upsert(CashflowStatementHot, items=items, unique_keys=["stock_code", "report_date", "report_type"])

    def batch_upsert_financial_metrics(self, items: list[dict]):
        return self.bulk_upsert(FinancialMetricHot, items=items, unique_keys=["stock_code", "report_date", "metric_name"])

    def batch_upsert_financial_notes(self, items: list[dict]):
        return self.bulk_upsert(FinancialNotesHot, items=items, unique_keys=["stock_code", "report_date", "note_type"])

    def batch_upsert_business_segments(self, items: list[dict]):
        return self.bulk_upsert(BusinessSegmentHot, items=items, unique_keys=["stock_code", "report_date", "segment_name", "segment_type"])

    def batch_upsert_stock_daily(self, items: list[dict]):
        return self.bulk_upsert(StockDailyHot, items=items, unique_keys=["stock_code", "trade_date"])
