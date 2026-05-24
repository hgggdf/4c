from __future__ import annotations

from datetime import date
from sqlalchemy import select

from app.core.database.models.financial_hot import FinancialHot, FinancialArchive
from app.core.repositories.base import BaseRepository


class FinancialRepository(BaseRepository):
    def list_income_statements(self, stock_code: str, *, limit: int = 4) -> list:
        hot_stmt = (select(FinancialHot)
                    .where(FinancialHot.stock_code == stock_code, FinancialHot.report_type != 'daily')
                    .order_by(FinancialHot.report_date.desc())
                    .limit(limit))
        cold_stmt = (select(FinancialArchive)
                     .where(FinancialArchive.stock_code == stock_code, FinancialArchive.report_type != 'daily')
                     .order_by(FinancialArchive.report_date.desc()))
        return self._hot_cold_list(hot_stmt, cold_stmt, limit=limit)

    def get_income_statements(self, stock_code: str, limit: int = 4) -> list:
        return self.list_income_statements(stock_code, limit=limit)

    def list_balance_sheets(self, stock_code: str, *, limit: int = 4) -> list:
        return self.list_income_statements(stock_code, limit=limit)

    def get_balance_sheets(self, stock_code: str, limit: int = 4) -> list:
        return self.list_income_statements(stock_code, limit=limit)

    def list_cashflow_statements(self, stock_code: str, *, limit: int = 4) -> list:
        return self.list_income_statements(stock_code, limit=limit)

    def get_cashflow_statements(self, stock_code: str, limit: int = 4) -> list:
        return self.list_income_statements(stock_code, limit=limit)

    def list_financial_metrics(self, stock_code: str, *, metric_names: list[str] | None = None, limit: int = 20) -> list:
        return self.list_income_statements(stock_code, limit=limit)

    def get_metrics(self, stock_code: str, metric_names: list[str] | None = None, limit: int = 20) -> list:
        return self.list_income_statements(stock_code, limit=limit)

    def list_business_segments(self, stock_code: str, *, limit: int = 20) -> list:
        return self.list_income_statements(stock_code, limit=limit)

    def get_business_segments(self, stock_code: str, limit: int = 20) -> list:
        return self.list_income_statements(stock_code, limit=limit)

    def list_financial_notes(self, stock_code: str, *, note_type: str | None = None, limit: int = 20) -> list:
        return self.list_income_statements(stock_code, limit=limit)

    def get_financial_note_by_id(self, note_id: int) -> FinancialHot | FinancialArchive | None:
        return self._hot_cold_get(FinancialHot, FinancialArchive, note_id)

    def list_stock_daily(self, stock_code: str, *, limit: int = 30) -> list:
        return []
