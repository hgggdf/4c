from __future__ import annotations

from sqlalchemy import select

from app.core.database.models.company import CompanyIndustryMap, CompanyMaster, CompanyProfile, IndustryMaster
from app.core.database.models.user import Watchlist
from app.core.repositories.base import BaseRepository


class CompanyWriteRepository(BaseRepository):
    def upsert_company_master(self, item: dict) -> tuple[CompanyMaster, bool]:
        unique = {"stock_code": item["stock_code"]}
        values = {k: v for k, v in item.items() if k not in unique and k != "id"}
        return self.upsert(CompanyMaster, unique_fields=unique, values=values)

    def batch_upsert_company_master(self, items: list[dict]) -> tuple[list[CompanyMaster], int, int]:
        return self.bulk_upsert(CompanyMaster, items=items, unique_keys=["stock_code"])

    def upsert_company_profile(self, item: dict) -> tuple[CompanyProfile, bool]:
        unique = {"stock_code": item["stock_code"]}
        values = {k: v for k, v in item.items() if k not in unique and k != "id"}
        return self.upsert(CompanyProfile, unique_fields=unique, values=values)

    def delete_company_profile(self, stock_code: str) -> list[int]:
        rows = self.list_by(CompanyProfile, stock_code=stock_code)
        deleted_ids = [row.id for row in rows]
        for row in rows:
            self.delete(row, flush=False)
        if deleted_ids:
            self.db.flush()
        return deleted_ids

    def batch_upsert_industries(self, items: list[dict]) -> tuple[list[IndustryMaster], int, int]:
        return self.bulk_upsert(IndustryMaster, items=items, unique_keys=["industry_code"])

    def replace_company_industries(self, stock_code: str, items: list[dict]) -> list[CompanyIndustryMap]:
        self.delete_where(CompanyIndustryMap, stock_code=stock_code)
        entities = [CompanyIndustryMap(stock_code=stock_code, **item) for item in items]
        return self.add_all(entities)

    def upsert_watchlist(self, item: dict) -> tuple[Watchlist, bool]:
        unique = {"user_id": item["user_id"], "stock_code": item["stock_code"]}
        values = {k: v for k, v in item.items() if k not in unique and k != "id"}
        return self.upsert(Watchlist, unique_fields=unique, values=values)

    def delete_watchlist(self, user_id: int, stock_code: str) -> list[int]:
        rows = self.list_by(Watchlist, user_id=user_id, stock_code=stock_code)
        deleted_ids = [row.id for row in rows]
        for row in rows:
            self.delete(row, flush=False)
        if deleted_ids:
            self.db.flush()
        return deleted_ids
