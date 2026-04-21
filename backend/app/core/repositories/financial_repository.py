from __future__ import annotations

from sqlalchemy import select

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


class FinancialRepository(BaseRepository):
    def list_income_statements(self, stock_code: str, *, limit: int = 4) -> list[IncomeStatementHot]:
        stmt = select(IncomeStatementHot).where(IncomeStatementHot.stock_code == stock_code)
        stmt = stmt.order_by(IncomeStatementHot.report_date.desc(), IncomeStatementHot.created_at.desc()).limit(limit)
        return self.scalars_all(stmt)

    def get_income_statements(self, stock_code: str, limit: int = 4) -> list[IncomeStatementHot]:
        return self.list_income_statements(stock_code, limit=limit)

    def list_balance_sheets(self, stock_code: str, *, limit: int = 4) -> list[BalanceSheetHot]:
        stmt = select(BalanceSheetHot).where(BalanceSheetHot.stock_code == stock_code)
        stmt = stmt.order_by(BalanceSheetHot.report_date.desc(), BalanceSheetHot.created_at.desc()).limit(limit)
        return self.scalars_all(stmt)

    def get_balance_sheets(self, stock_code: str, limit: int = 4) -> list[BalanceSheetHot]:
        return self.list_balance_sheets(stock_code, limit=limit)

    def list_cashflow_statements(self, stock_code: str, *, limit: int = 4) -> list[CashflowStatementHot]:
        stmt = select(CashflowStatementHot).where(CashflowStatementHot.stock_code == stock_code)
        stmt = stmt.order_by(CashflowStatementHot.report_date.desc(), CashflowStatementHot.created_at.desc()).limit(limit)
        return self.scalars_all(stmt)

    def get_cashflow_statements(self, stock_code: str, limit: int = 4) -> list[CashflowStatementHot]:
        return self.list_cashflow_statements(stock_code, limit=limit)

    def list_financial_metrics(self, stock_code: str, *, metric_names: list[str] | None = None, limit: int = 20) -> list[FinancialMetricHot]:
        stmt = select(FinancialMetricHot).where(FinancialMetricHot.stock_code == stock_code)
        if metric_names:
            stmt = stmt.where(FinancialMetricHot.metric_name.in_(metric_names))
        stmt = stmt.order_by(FinancialMetricHot.report_date.desc(), FinancialMetricHot.created_at.desc()).limit(limit)
        return self.scalars_all(stmt)

    def get_metrics(self, stock_code: str, metric_names: list[str] | None = None, limit: int = 20) -> list[FinancialMetricHot]:
        return self.list_financial_metrics(stock_code, metric_names=metric_names, limit=limit)

    def list_business_segments(self, stock_code: str, *, limit: int = 20) -> list[BusinessSegmentHot]:
        stmt = select(BusinessSegmentHot).where(BusinessSegmentHot.stock_code == stock_code)
        stmt = stmt.order_by(BusinessSegmentHot.report_date.desc(), BusinessSegmentHot.created_at.desc()).limit(limit)
        return self.scalars_all(stmt)

    def get_business_segments(self, stock_code: str, limit: int = 20) -> list[BusinessSegmentHot]:
        return self.list_business_segments(stock_code, limit=limit)

    def list_financial_notes(self, stock_code: str, *, note_type: str | None = None, limit: int = 20) -> list[FinancialNotesHot]:
        stmt = select(FinancialNotesHot).where(FinancialNotesHot.stock_code == stock_code)
        if note_type:
            stmt = stmt.where(FinancialNotesHot.note_type == note_type)
        stmt = stmt.order_by(FinancialNotesHot.report_date.desc(), FinancialNotesHot.created_at.desc()).limit(limit)
        return self.scalars_all(stmt)

    def get_financial_note_by_id(self, note_id: int) -> FinancialNotesHot | None:
        stmt = select(FinancialNotesHot).where(FinancialNotesHot.id == note_id)
        return self.scalar_one_or_none(stmt)

    def list_stock_daily(self, stock_code: str, *, limit: int = 30) -> list[StockDailyHot]:
        stmt = select(StockDailyHot).where(StockDailyHot.stock_code == stock_code)
        stmt = stmt.order_by(StockDailyHot.trade_date.desc(), StockDailyHot.created_at.desc()).limit(limit)
        return self.scalars_all(stmt)
