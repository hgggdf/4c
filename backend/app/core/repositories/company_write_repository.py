from __future__ import annotations

from app.core.database.models.company import Company, CompanyMaster, IndustryMaster
from app.core.database.models.user import Watchlist
from app.core.repositories.base import BaseRepository


class CompanyWriteRepository(BaseRepository):
    """公司、行业和自选股写库入口。"""

    def upsert_company_master(self, item: dict) -> tuple[Company, bool]:
        """写入或更新公司主数据，按 stock_code 去重。"""
        unique = {"stock_code": item["stock_code"]}
        values = {k: v for k, v in item.items() if k not in unique and k != "id"}
        return self.upsert(Company, unique_fields=unique, values=values)

    def batch_upsert_company_master(self, items: list[dict]) -> tuple[list[Company], int, int]:
        """批量写入公司主数据，按 stock_code 去重。"""
        return self.bulk_upsert(Company, items=items, unique_keys=["stock_code"])

    def upsert_company_profile(self, item: dict) -> tuple[Company, bool]:
        """写入或更新公司画像字段；v3 中画像字段合并到 company 表。"""
        # v3: profile 字段合并到 company 表
        unique = {"stock_code": item["stock_code"]}
        values = {k: v for k, v in item.items() if k not in unique and k != "id"}
        return self.upsert(Company, unique_fields=unique, values=values)

    def delete_company_profile(self, stock_code: str) -> list[int]:
        """清空指定公司的画像字段，保留公司主记录。"""
        # v3: 无独立 profile 表，清空画像字段
        rows = self.list_by(Company, stock_code=stock_code)
        for row in rows:
            row.business_summary = None
            row.core_products_json = None
            row.main_segments_json = None
        self.db.flush()
        return [row.stock_code for row in rows]

    def batch_upsert_industries(self, items: list[dict]) -> tuple[list[IndustryMaster], int, int]:
        """批量写入行业主数据，按 industry_code 去重。"""
        return self.bulk_upsert(IndustryMaster, items=items, unique_keys=["industry_code"])

    def replace_company_industries(self, stock_code: str, items: list[dict]) -> list:
        """替换公司所属行业；v3 company 表只保留一个 industry_code。"""
        # v3: company 只有一个 industry_code，取第一个 primary 行业
        if not items:
            return []
        primary = next((i for i in items if i.get("is_primary", 1)), items[0])
        row = self.get_one_by(Company, stock_code=stock_code)
        if row:
            row.industry_code = primary.get("industry_code")
            self.db.flush()
        return [row] if row else []

    def upsert_watchlist(self, item: dict) -> tuple[Watchlist, bool]:
        """写入或更新用户自选股，按 user_id + stock_code 去重。"""
        unique = {"user_id": item["user_id"], "stock_code": item["stock_code"]}
        values = {k: v for k, v in item.items() if k not in unique and k != "id"}
        return self.upsert(Watchlist, unique_fields=unique, values=values)

    def delete_watchlist(self, user_id: int, stock_code: str) -> list[int]:
        """删除用户指定股票的自选记录。"""
        rows = self.list_by(Watchlist, user_id=user_id, stock_code=stock_code)
        deleted_ids = [row.id for row in rows]
        for row in rows:
            self.delete(row, flush=False)
        if deleted_ids:
            self.db.flush()
        return deleted_ids
