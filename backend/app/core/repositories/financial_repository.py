from __future__ import annotations

from datetime import date
from sqlalchemy import select

from app.core.database.models.financial_hot import FinancialHot, FinancialArchive
from app.core.repositories.base import BaseRepository


class FinancialRepository(BaseRepository):
    """财务和行情读库入口。

    v3 将多类财务数据合并到 financial_hot / financial_archive。
    当前读接口多数复用 list_income_statements，按非 daily 报告记录返回。
    """

    def list_income_statements(self, stock_code: str, *, limit: int = 4) -> list:
        """查询指定股票最近的非日行情财务记录，热库不足时补冷库。"""
        hot_stmt = (select(FinancialHot)
                    .where(FinancialHot.stock_code == stock_code, FinancialHot.report_type != 'daily')
                    .order_by(FinancialHot.report_date.desc())
                    .limit(limit))
        cold_stmt = (select(FinancialArchive)
                     .where(FinancialArchive.stock_code == stock_code, FinancialArchive.report_type != 'daily')
                     .order_by(FinancialArchive.report_date.desc()))
        return self._hot_cold_list(hot_stmt, cold_stmt, limit=limit)

    def get_income_statements(self, stock_code: str, limit: int = 4) -> list:
        """收入表查询兼容入口。"""
        return self.list_income_statements(stock_code, limit=limit)

    def list_balance_sheets(self, stock_code: str, *, limit: int = 4) -> list:
        """资产负债表查询兼容入口；v3 暂复用合并财务记录。"""
        return self.list_income_statements(stock_code, limit=limit)

    def get_balance_sheets(self, stock_code: str, limit: int = 4) -> list:
        """资产负债表 service 调用入口。"""
        return self.list_income_statements(stock_code, limit=limit)

    def list_cashflow_statements(self, stock_code: str, *, limit: int = 4) -> list:
        """现金流量表查询兼容入口；v3 暂复用合并财务记录。"""
        return self.list_income_statements(stock_code, limit=limit)

    def get_cashflow_statements(self, stock_code: str, limit: int = 4) -> list:
        """现金流量表 service 调用入口。"""
        return self.list_income_statements(stock_code, limit=limit)

    def list_financial_metrics(self, stock_code: str, *, metric_names: list[str] | None = None, limit: int = 20) -> list:
        """财务指标查询兼容入口；metric_names 当前未在 repository 层过滤。"""
        return self.list_income_statements(stock_code, limit=limit)

    def get_metrics(self, stock_code: str, metric_names: list[str] | None = None, limit: int = 20) -> list:
        """财务指标 service 调用入口。"""
        return self.list_income_statements(stock_code, limit=limit)

    def list_business_segments(self, stock_code: str, *, limit: int = 20) -> list:
        """业务分部查询兼容入口；v3 暂复用合并财务记录。"""
        return self.list_income_statements(stock_code, limit=limit)

    def get_business_segments(self, stock_code: str, limit: int = 20) -> list:
        """业务分部 service 调用入口。"""
        return self.list_income_statements(stock_code, limit=limit)

    def list_financial_notes(self, stock_code: str, *, note_type: str | None = None, limit: int = 20) -> list:
        """财务附注查询兼容入口；note_type 当前未在 repository 层过滤。"""
        return self.list_income_statements(stock_code, limit=limit)

    def get_financial_note_by_id(self, note_id: int) -> FinancialHot | FinancialArchive | None:
        """按 id 查询财务记录详情，热库未命中时查冷库。"""
        return self._hot_cold_get(FinancialHot, FinancialArchive, note_id)

    def list_stock_daily(self, stock_code: str, *, limit: int = 30) -> list:
        """日行情读取占位入口。

        当前返回空列表；前端 K 线另走 stock_service/shared 中的查询逻辑。
        """
        return []
