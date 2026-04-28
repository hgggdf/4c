from __future__ import annotations

from app.core.repositories.company_repository import CompanyRepository

from .base import BaseService
from .guards import require_non_empty


class CompanyService(BaseService):
    def get_company_basic_info(self, stock_code: str):
        return self._run(lambda: self._get_company_basic_info(stock_code))

    def get_company_profile(self, stock_code: str):
        return self._run(lambda: self._get_company_profile(stock_code))

    def get_company_industries(self, stock_code: str):
        return self._run(lambda: self._get_company_industries(stock_code))

    def get_company_overview(self, stock_code: str):
        return self._run(lambda: self._get_company_overview(stock_code))

    def resolve_company(self, text: str):
        """
        给 RetrievalService / ChatService 用的公司识别接口。
        """
        return self._run(lambda: self._resolve_company(text))

    def ensure_company_exists(self, stock_code: str):
        return self._run(lambda: self._ensure_company_exists(stock_code))

    def _get_company_basic_info(self, stock_code: str):
        stock_code = require_non_empty(stock_code, "stock_code")
        return self._with_db(lambda db: self._query_company_basic_info(db, stock_code))

    def _get_company_profile(self, stock_code: str):
        stock_code = require_non_empty(stock_code, "stock_code")
        return self._with_db(lambda db: self._query_company_profile(db, stock_code))

    def _get_company_industries(self, stock_code: str):
        stock_code = require_non_empty(stock_code, "stock_code")
        return self._with_db(lambda db: self._query_company_industries(db, stock_code))

    def _get_company_overview(self, stock_code: str):
        stock_code = require_non_empty(stock_code, "stock_code")
        return self._with_db(lambda db: self._query_company_overview(db, stock_code))

    def _resolve_company(self, text: str):
        text = require_non_empty(text, "text")
        return self._with_db(lambda db: self._query_resolve_company(db, text))

    def _ensure_company_exists(self, stock_code: str):
        stock_code = require_non_empty(stock_code, "stock_code")
        return self._with_db(lambda db: self._query_ensure_company_exists(db, stock_code))

    def _query_company_basic_info(self, db, stock_code: str):
        repo = CompanyRepository(db)
        company = repo.get_by_stock_code(stock_code)
        if company is None:
            raise ValueError(f"company not found: {stock_code}")

        return {
            "stock_code": company.stock_code,
            "stock_name": company.stock_name,
            "full_name": company.full_name,
            "exchange": company.exchange,
            "industry_level1": company.industry_level1,
            "industry_level2": company.industry_level2,
            "listing_date": company.listing_date,
            "status": company.status,
            "alias_json": company.alias_json,
        }

    def _query_company_profile(self, db, stock_code: str):
        repo = CompanyRepository(db)
        profile = repo.get_profile(stock_code)
        if profile is None:
            return None

        return {
            "stock_code": profile.stock_code,
            "business_summary": profile.business_summary,
            "core_products_json": profile.core_products_json,
            "main_segments_json": profile.main_segments_json,
            "market_position": profile.market_position,
            "management_summary": profile.management_summary,
        }

    def _query_company_industries(self, db, stock_code: str):
        repo = CompanyRepository(db)
        rows = repo.list_industries(stock_code)
        return [
            {
                "industry_code": r.industry_code,
                "industry_name": r.industry_name,
                "parent_industry_code": r.parent_industry_code,
                "description": r.description,
            }
            for r in rows
        ]

    def _query_company_overview(self, db, stock_code: str):
        repo = CompanyRepository(db)
        company = repo.get_by_stock_code(stock_code)
        if company is None:
            raise ValueError(f"company not found: {stock_code}")

        profile = repo.get_profile(stock_code)
        industries = repo.list_industries(stock_code)

        return {
            "stock_code": company.stock_code,
            "stock_name": company.stock_name,
            "full_name": company.full_name,
            "exchange": company.exchange,
            "industry_level1": company.industry_level1,
            "industry_level2": company.industry_level2,
            "listing_date": company.listing_date,
            "status": company.status,
            "alias_json": company.alias_json,
            "profile": None
            if profile is None
            else {
                "business_summary": profile.business_summary,
                "core_products_json": profile.core_products_json,
                "main_segments_json": profile.main_segments_json,
                "market_position": profile.market_position,
                "management_summary": profile.management_summary,
            },
            "industries": [
                {
                    "industry_code": r.industry_code,
                    "industry_name": r.industry_name,
                    "parent_industry_code": r.parent_industry_code,
                    "description": r.description,
                }
                for r in industries
            ],
        }

    def _query_resolve_company(self, db, text: str):
        repo = CompanyRepository(db)
        rows = repo.resolve_company_from_text(text)

        return [
            {
                "stock_code": row.stock_code,
                "stock_name": row.stock_name,
                "full_name": row.full_name,
                "exchange": row.exchange,
                "industry_level1": row.industry_level1,
                "industry_level2": row.industry_level2,
                "alias_json": row.alias_json,
            }
            for row in rows
        ]

    def _query_ensure_company_exists(self, db, stock_code: str):
        repo = CompanyRepository(db)
        company = repo.get_by_stock_code(stock_code)
        return company is not None
