from __future__ import annotations

from app.core.repositories import FinancialRepository

from .base import BaseService
from .guards import require_positive_int, require_stock_code
from .requests import FinancialMetricsRequest, FinancialSummaryRequest, StockCodeLimitRequest, StockCodeRequest
from .serializers import model_to_dict


class FinancialService(BaseService):
    def __init__(self, *, ctx, company_service=None) -> None:
        super().__init__(ctx=ctx)
        self.company_service = company_service

    def get_income_statements(self, req: StockCodeLimitRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_income_statements(db, req)), trace_id=req.trace_id)

    def get_balance_sheets(self, req: StockCodeLimitRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_balance_sheets(db, req)), trace_id=req.trace_id)

    def get_cashflow_statements(self, req: StockCodeLimitRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_cashflow_statements(db, req)), trace_id=req.trace_id)

    def get_financial_metrics(self, req: FinancialMetricsRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_financial_metrics(db, req)), trace_id=req.trace_id)

    def get_business_segments(self, req: StockCodeLimitRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_business_segments(db, req)), trace_id=req.trace_id)

    def get_financial_summary(self, req: FinancialSummaryRequest):
        return self._run(lambda: self._with_db(lambda db: self._get_financial_summary(db, req)), trace_id=req.trace_id)

    def _ensure_company(self, stock_code: str) -> None:
        if self.company_service:
            ok = self.company_service.ensure_company_exists(stock_code).data
            if not ok:
                raise ValueError(f"company not found: {stock_code}")

    def _get_income_statements(self, db, req: StockCodeLimitRequest) -> list[dict]:
        stock_code = require_stock_code(req.stock_code)
        limit = require_positive_int(req.limit, "limit")
        self._ensure_company(stock_code)
        rows = FinancialRepository(db).get_income_statements(stock_code, limit=limit)
        fields = ["stock_code", "report_date", "fiscal_year", "report_type", "revenue", "operating_cost", "gross_profit", "selling_expense", "admin_expense", "rd_expense", "operating_profit", "net_profit", "net_profit_deducted", "eps", "source_type", "source_url", "created_at"]
        return [model_to_dict(r, fields) for r in rows]

    def _get_balance_sheets(self, db, req: StockCodeLimitRequest) -> list[dict]:
        stock_code = require_stock_code(req.stock_code)
        limit = require_positive_int(req.limit, "limit")
        self._ensure_company(stock_code)
        rows = FinancialRepository(db).get_balance_sheets(stock_code, limit=limit)
        fields = ["stock_code", "report_date", "fiscal_year", "report_type", "total_assets", "total_liabilities", "accounts_receivable", "inventory", "cash", "equity", "goodwill", "source_type", "source_url", "created_at"]
        return [model_to_dict(r, fields) for r in rows]

    def _get_cashflow_statements(self, db, req: StockCodeLimitRequest) -> list[dict]:
        stock_code = require_stock_code(req.stock_code)
        limit = require_positive_int(req.limit, "limit")
        self._ensure_company(stock_code)
        rows = FinancialRepository(db).get_cashflow_statements(stock_code, limit=limit)
        fields = ["stock_code", "report_date", "fiscal_year", "report_type", "operating_cashflow", "investing_cashflow", "financing_cashflow", "free_cashflow", "source_type", "source_url", "created_at"]
        return [model_to_dict(r, fields) for r in rows]

    def _get_financial_metrics(self, db, req: FinancialMetricsRequest) -> list[dict]:
        stock_code = require_stock_code(req.stock_code)
        limit = require_positive_int(req.limit, "limit")
        if not req.metric_names:
            raise ValueError("metric_names is required")
        self._ensure_company(stock_code)
        rows = FinancialRepository(db).get_metrics(stock_code, req.metric_names, limit=limit)
        fields = ["stock_code", "report_date", "fiscal_year", "metric_name", "metric_value", "metric_unit", "calc_method", "source_ref_json", "created_at"]
        return [model_to_dict(r, fields) for r in rows]

    def _get_business_segments(self, db, req: StockCodeLimitRequest) -> list[dict]:
        stock_code = require_stock_code(req.stock_code)
        limit = require_positive_int(req.limit, "limit")
        self._ensure_company(stock_code)
        rows = FinancialRepository(db).get_business_segments(stock_code, limit=limit)
        fields = ["stock_code", "report_date", "segment_name", "segment_type", "revenue", "revenue_ratio", "gross_margin", "source_type", "source_url", "created_at"]
        return [model_to_dict(r, fields) for r in rows]

    def _get_financial_summary(self, db, req: FinancialSummaryRequest) -> dict:
        stock_code = require_stock_code(req.stock_code)
        count = require_positive_int(req.period_count, "period_count")
        self._ensure_company(stock_code)
        repo = FinancialRepository(db)
        income = [model_to_dict(r, ["report_date", "fiscal_year", "report_type", "revenue", "gross_profit", "net_profit", "net_profit_deducted", "rd_expense", "eps"]) for r in repo.get_income_statements(stock_code, limit=count)]
        balance = [model_to_dict(r, ["report_date", "fiscal_year", "report_type", "total_assets", "total_liabilities", "cash", "equity", "goodwill"]) for r in repo.get_balance_sheets(stock_code, limit=count)]
        cashflows = [model_to_dict(r, ["report_date", "fiscal_year", "report_type", "operating_cashflow", "investing_cashflow", "financing_cashflow", "free_cashflow"]) for r in repo.get_cashflow_statements(stock_code, limit=count)]
        key_metrics = [model_to_dict(r, ["report_date", "fiscal_year", "metric_name", "metric_value", "metric_unit"]) for r in repo.get_metrics(stock_code, ["gross_margin", "net_margin", "rd_ratio", "debt_ratio", "roe"], limit=count*5)]
        latest_income = {"stock_code": stock_code, **income[0]} if income else None
        latest_balance = {"stock_code": stock_code, **balance[0]} if balance else None
        latest_cashflow = {"stock_code": stock_code, **cashflows[0]} if cashflows else None
        return {
            "stock_code": stock_code,
            "latest_income": latest_income,
            "latest_balance": latest_balance,
            "latest_cashflow": latest_cashflow,
            "income_statements": income,
            "balance_sheets": balance,
            "cashflow_statements": cashflows,
            "key_metrics": key_metrics,
        }
