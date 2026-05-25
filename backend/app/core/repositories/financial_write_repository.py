from __future__ import annotations

from app.core.database.models.financial_hot import FinancialHot, FinancialArchive
from app.core.repositories.base import BaseRepository
from app.core.utils.dedup import prepare_dedup_record


def _prepare_financial_items(items: list[dict]) -> list[dict]:
    return [prepare_dedup_record("financial", item) for item in items]


class FinancialWriteRepository(BaseRepository):
    """财务写库入口。

    v3 将收入表、资产负债表、现金流、指标、附注、分部等合并写入 FinancialHot。
    默认去重键为 stock_code + report_date + report_type。
    """

    def batch_upsert_income_statements(self, items: list[dict]):
        """批量写入收入表数据，按 stock_code/report_date/report_type 去重。"""
        return self.bulk_upsert(FinancialHot, items=_prepare_financial_items(items), unique_keys=["dedup_key"])

    def batch_upsert_balance_sheets(self, items: list[dict]):
        """批量写入资产负债表数据，复用 FinancialHot 合并表。"""
        return self.bulk_upsert(FinancialHot, items=_prepare_financial_items(items), unique_keys=["dedup_key"])

    def batch_upsert_cashflow_statements(self, items: list[dict]):
        """批量写入现金流量表数据，复用 FinancialHot 合并表。"""
        return self.bulk_upsert(FinancialHot, items=_prepare_financial_items(items), unique_keys=["dedup_key"])

    def batch_upsert_financial(self, items: list[dict]):
        """通用财务批量写入入口。"""
        return self.bulk_upsert(FinancialHot, items=_prepare_financial_items(items), unique_keys=["dedup_key"])

    def batch_upsert_financial_metrics(self, items: list[dict]):
        """批量写入财务指标数据，复用 FinancialHot 合并表。"""
        return self.bulk_upsert(FinancialHot, items=_prepare_financial_items(items), unique_keys=["dedup_key"])

    def batch_upsert_financial_notes(self, items: list[dict]):
        """批量写入财务附注数据，复用 FinancialHot 合并表。"""
        return self.bulk_upsert(FinancialHot, items=_prepare_financial_items(items), unique_keys=["dedup_key"])

    def batch_upsert_business_segments(self, items: list[dict]):
        """批量写入业务分部数据，复用 FinancialHot 合并表。"""
        return self.bulk_upsert(FinancialHot, items=_prepare_financial_items(items), unique_keys=["dedup_key"])

    def batch_upsert_stock_daily(self, items: list[dict]):
        """日行情写入占位入口；当前没有实际写库行为。"""
        # v3 无 stock_daily 表，静默忽略
        return [], 0, 0

    def batch_delete_income_statements(self, items: list[dict]) -> list[int]:
        """按财务唯一键批量删除收入表兼容数据。"""
        return self._batch_delete(FinancialHot, items, ["stock_code", "report_date", "report_type"])

    def batch_delete_balance_sheets(self, items: list[dict]) -> list[int]:
        """按财务唯一键批量删除资产负债表兼容数据。"""
        return self._batch_delete(FinancialHot, items, ["stock_code", "report_date", "report_type"])

    def batch_delete_cashflow_statements(self, items: list[dict]) -> list[int]:
        """按财务唯一键批量删除现金流兼容数据。"""
        return self._batch_delete(FinancialHot, items, ["stock_code", "report_date", "report_type"])

    def batch_delete_financial_metrics(self, items: list[dict]) -> list[int]:
        """按财务唯一键批量删除指标兼容数据。"""
        return self._batch_delete(FinancialHot, items, ["stock_code", "report_date", "report_type"])

    def batch_delete_financial_notes(self, items: list[dict]) -> list[int]:
        """按财务唯一键批量删除附注兼容数据。"""
        return self._batch_delete(FinancialHot, items, ["stock_code", "report_date", "report_type"])

    def batch_delete_business_segments(self, items: list[dict]) -> list[int]:
        """按财务唯一键批量删除业务分部兼容数据。"""
        return self._batch_delete(FinancialHot, items, ["stock_code", "report_date", "report_type"])

    def batch_delete_stock_daily(self, items: list[dict]) -> list[int]:
        """日行情删除占位入口；当前没有实际删除行为。"""
        return []

    def _batch_delete(self, model, items: list[dict], key_fields: list[str]) -> list[int]:
        """按给定 key_fields 逐条查找并删除匹配记录，返回删除的 id。"""
        deleted_ids: list[int] = []
        for item in items:
            for row in self.list_by(model, **{k: item.get(k) for k in key_fields}):
                deleted_ids.append(row.id)
                self.delete(row, flush=False)
        if deleted_ids:
            self.db.flush()
        return deleted_ids
