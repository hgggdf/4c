from __future__ import annotations

from datetime import date
from sqlalchemy import select

from app.core.database.models.financial_hot import FinancialHot, FinancialArchive
from app.core.repositories.base import BaseRepository


class FinancialRepository(BaseRepository):
    def list_income_statements(self, stock_code: str, *, limit: int = 4) -> list[FinancialHot]:
        stmt = (select(FinancialHot)
                .where(FinancialHot.stock_code == stock_code,
                       FinancialHot.report_type != 'daily')
                .order_by(FinancialHot.report_date.desc())
                .limit(limit))
        return self.scalars_all(stmt)

    def get_income_statements(self, stock_code: str, limit: int = 4) -> list[FinancialHot]:
        return self.list_income_statements(stock_code, limit=limit)

    # 旧版三表拆分的方法，全部查 financial_hot 同一张表
    def list_balance_sheets(self, stock_code: str, *, limit: int = 4) -> list[FinancialHot]:
        return self.list_income_statements(stock_code, limit=limit)

    def get_balance_sheets(self, stock_code: str, limit: int = 4) -> list[FinancialHot]:
        return self.list_income_statements(stock_code, limit=limit)

    def list_cashflow_statements(self, stock_code: str, *, limit: int = 4) -> list[FinancialHot]:
        return self.list_income_statements(stock_code, limit=limit)

    def get_cashflow_statements(self, stock_code: str, limit: int = 4) -> list[FinancialHot]:
        return self.list_income_statements(stock_code, limit=limit)

    # 旧版 financial_metric_hot → 直接从 financial_hot 返回，调用方按 metric_name 过滤
    def list_financial_metrics(self, stock_code: str, *, metric_names: list[str] | None = None, limit: int = 20) -> list[FinancialHot]:
        return self.list_income_statements(stock_code, limit=limit)

    def get_metrics(self, stock_code: str, metric_names: list[str] | None = None, limit: int = 20) -> list[FinancialHot]:
        return self.list_income_statements(stock_code, limit=limit)

    # 旧版 business_segment_hot → financial_hot
    def list_business_segments(self, stock_code: str, *, limit: int = 20) -> list[FinancialHot]:
        return self.list_income_statements(stock_code, limit=limit)

    def get_business_segments(self, stock_code: str, limit: int = 20) -> list[FinancialHot]:
        return self.list_income_statements(stock_code, limit=limit)

    # 旧版 financial_notes_hot → financial_hot
    def list_financial_notes(self, stock_code: str, *, note_type: str | None = None, limit: int = 20) -> list[FinancialHot]:
        return self.list_income_statements(stock_code, limit=limit)

    def get_financial_note_by_id(self, note_id: int) -> FinancialHot | None:
        return self.scalar_one_or_none(select(FinancialHot).where(FinancialHot.id == note_id))

    # 旧版 stock_daily_hot → 返回空列表（v3 无此表）
    def list_stock_daily(self, stock_code: str, *, limit: int = 30) -> list:
        return []
