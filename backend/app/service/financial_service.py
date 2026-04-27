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
        fields = ["id", "stock_code", "report_date", "fiscal_year", "report_type", "revenue", "operating_cost", "gross_profit", "gross_margin", "selling_expense", "admin_expense", "rd_expense", "rd_ratio", "operating_profit", "net_profit", "net_profit_deducted", "net_margin", "eps", "source_type", "source_url", "file_hash", "created_at"]
        return [model_to_dict(r, fields) for r in rows]

    def _get_balance_sheets(self, db, req: StockCodeLimitRequest) -> list[dict]:
        stock_code = require_stock_code(req.stock_code)
        limit = require_positive_int(req.limit, "limit")
        self._ensure_company(stock_code)
        rows = FinancialRepository(db).get_balance_sheets(stock_code, limit=limit)
        fields = ["id", "stock_code", "report_date", "fiscal_year", "report_type", "total_assets", "total_liabilities", "debt_ratio", "accounts_receivable", "inventory", "cash", "equity", "goodwill", "source_type", "source_url", "file_hash", "created_at"]
        return [model_to_dict(r, fields) for r in rows]

    def _get_cashflow_statements(self, db, req: StockCodeLimitRequest) -> list[dict]:
        stock_code = require_stock_code(req.stock_code)
        limit = require_positive_int(req.limit, "limit")
        self._ensure_company(stock_code)
        rows = FinancialRepository(db).get_cashflow_statements(stock_code, limit=limit)
        fields = ["id", "stock_code", "report_date", "fiscal_year", "report_type", "operating_cashflow", "investing_cashflow", "financing_cashflow", "free_cashflow", "source_type", "source_url", "file_hash", "created_at"]
        return [model_to_dict(r, fields) for r in rows]

    def _get_financial_metrics(self, db, req: FinancialMetricsRequest) -> list[dict]:
        stock_code = require_stock_code(req.stock_code)
        limit = require_positive_int(req.limit, "limit")
        if not req.metric_names:
            raise ValueError("metric_names is required")
        self._ensure_company(stock_code)
        rows = FinancialRepository(db).get_metrics(stock_code, req.metric_names, limit=limit)

        METRIC_COLUMN_MAP = {
            "gross_margin": ("gross_margin", "ratio"),
            "net_margin": (None, "ratio"),  # 需计算
            "roe": (None, "ratio"),
            "rd_ratio": ("rd_ratio", "ratio"),
            "debt_ratio": ("debt_ratio", "ratio"),
            "revenue": ("revenue", "yuan"),
            "net_profit": ("net_profit", "yuan"),
            "eps": ("eps", "yuan"),
            "operating_cashflow": ("operating_cashflow", "yuan"),
        }

        results = []
        for row in rows:
            for metric_name in req.metric_names:
                col_info = METRIC_COLUMN_MAP.get(metric_name)
                if col_info:
                    col, unit = col_info
                    if col:
                        value = getattr(row, col, None)
                    elif metric_name == "net_margin":
                        np = getattr(row, "net_profit", None)
                        rev = getattr(row, "revenue", None)
                        value = float(np) / float(rev) if np and rev and float(rev) != 0 else None
                    elif metric_name == "roe":
                        np = getattr(row, "net_profit", None)
                        ta = getattr(row, "total_assets", None)
                        value = float(np) / float(ta) if np and ta and float(ta) != 0 else None
                    else:
                        value = None
                else:
                    value = getattr(row, metric_name, None)
                    unit = None

                if value is not None:
                    from .serializers import normalize_value
                    results.append({
                        "stock_code": stock_code,
                        "report_date": normalize_value(row.report_date),
                        "fiscal_year": row.fiscal_year,
                        "metric_name": metric_name,
                        "metric_value": normalize_value(value),
                        "metric_unit": unit,
                        "created_at": normalize_value(row.created_at),
                    })
        return results

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
        _fields = ["report_date", "fiscal_year", "report_type",
                   "revenue", "operating_cost", "gross_profit", "gross_margin",
                   "selling_expense", "admin_expense", "rd_expense", "rd_ratio",
                   "operating_profit", "net_profit", "net_profit_deducted", "eps",
                   "total_assets", "total_liabilities", "debt_ratio",
                   "operating_cashflow", "investing_cashflow", "financing_cashflow"]
        rows = repo.get_income_statements(stock_code, limit=count)
        statements = [model_to_dict(r, _fields) for r in rows]

        # compute net_margin and roe inline
        for s in statements:
            rev = s.get("revenue")
            np_ = s.get("net_profit")
            ta  = s.get("total_assets")
            tl  = s.get("total_liabilities")
            s["net_margin"] = round(float(np_) / float(rev), 6) if np_ and rev and float(rev) != 0 else None
            equity = (float(ta) - float(tl)) if ta and tl else None
            s["roe"] = round(float(np_) / equity, 6) if np_ and equity and equity != 0 else None

        latest = {"stock_code": stock_code, **statements[0]} if statements else None
        return {
            "stock_code": stock_code,
            "latest_income": latest,
            "latest_balance": latest,
            "latest_cashflow": latest,
            "income_statements": statements,
            "balance_sheets": statements,
            "cashflow_statements": statements,
            "key_metrics": [
                {"report_date": s["report_date"], "fiscal_year": s["fiscal_year"],
                 "gross_margin": s.get("gross_margin"), "net_margin": s.get("net_margin"),
                 "rd_ratio": s.get("rd_ratio"), "debt_ratio": s.get("debt_ratio"),
                 "roe": s.get("roe")}
                for s in statements
            ],
        }
