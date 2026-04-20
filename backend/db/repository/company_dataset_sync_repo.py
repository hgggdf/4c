from __future__ import annotations

import json
import re
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models.announcement import AnnouncementRaw
from db.models.financial_statement import (
    BalanceSheet,
    CashflowStatement,
    FinancialNotes,
    IncomeStatement,
)
from db.repository.financial_repo import FinancialDataRepository


class CompanyDatasetSyncRepository:
    def __init__(self) -> None:
        self.financial_repo = FinancialDataRepository()

    def sync_financial_data(self, db: Session, data: dict) -> None:
        records = self._build_financial_records(data)
        if records:
            self.financial_repo.batch_upsert(db, records, commit=False)

    def sync_structured_dataset(self, db: Session, data: dict) -> bool:
        changed = False
        changed = self._sync_announcements(db, data) or changed

        changed = self._sync_statement_rows(
            db,
            data,
            section="profit_sheet",
            model=IncomeStatement,
            field_aliases={
                "revenue": ("revenue", "total_revenue", "operate_income", "operateincome", "OPERATE_INCOME", "营业总收入", "营业收入"),
                "operating_cost": ("operating_cost", "total_operating_cost", "operate_cost", "operatecost", "OPERATE_EXPENSE", "营业总成本", "营业成本"),
                "gross_profit": ("gross_profit", "grossprofit", "毛利", "毛利润"),
                "selling_expense": ("selling_expense", "sale_expense", "saleexpense", "销售费用"),
                "admin_expense": ("admin_expense", "manage_expense", "manageexpense", "管理费用"),
                "rd_expense": ("rd_expense", "research_expense", "researchexpense", "研发费用"),
                "net_profit": ("net_profit", "parent_netprofit", "parentnetprofit", "PARENT_NETPROFIT", "NETPROFIT", "净利润", "归母净利润"),
                "net_profit_deducted": ("net_profit_deducted", "deduct_parent_netprofit", "deductparentnetprofit", "DEDUCT_PARENT_NETPROFIT", "扣非净利润", "扣除非经常性损益后的净利润"),
            },
        ) or changed

        changed = self._sync_statement_rows(
            db,
            data,
            section="balance_sheet",
            model=BalanceSheet,
            field_aliases={
                "total_assets": ("total_assets", "asset_total", "assettotal", "TOTAL_ASSETS", "总资产", "资产总计"),
                "total_liabilities": ("total_liabilities", "liability_total", "liabilitytotal", "TOTAL_LIABILITIES", "总负债", "负债合计"),
                "accounts_receivable": ("accounts_receivable", "accountsreceivable", "应收账款"),
                "inventory": ("inventory", "存货"),
                "cash": ("cash", "cash_equivalents", "cashequivalents", "货币资金", "现金及现金等价物"),
                "equity": ("equity", "total_equity", "totalequity", "所有者权益", "股东权益"),
            },
        ) or changed

        changed = self._sync_statement_rows(
            db,
            data,
            section="cash_flow_sheet",
            model=CashflowStatement,
            field_aliases={
                "operating_cashflow": ("operating_cashflow", "netcash_operate", "NETCASH_OPERATE", "net_operate_cash_flow", "经营活动产生的现金流量净额"),
                "investing_cashflow": ("investing_cashflow", "netcash_invest", "NETCASH_INVEST", "net_invest_cash_flow", "投资活动产生的现金流量净额"),
                "financing_cashflow": ("financing_cashflow", "netcash_finance", "NETCASH_FINANCE", "net_finance_cash_flow", "筹资活动产生的现金流量净额"),
            },
        ) or changed

        return changed

    def _sync_announcements(self, db: Session, data: dict) -> bool:
        stock_code = data.get("symbol")
        if not stock_code:
            return False

        changed = False
        for item in data.get("announcements", []):
            if not isinstance(item, dict):
                continue

            title = self._stringify(
                self._first_value(item, ("title", "name", "公告标题", "公告名称"))
            )
            if not title:
                continue

            publish_date = self._extract_date(item)
            content = self._stringify(
                self._first_value(item, ("content", "summary", "内容", "摘要"))
            )

            row = self._upsert_model(
                db,
                AnnouncementRaw,
                lookup={
                    "stock_code": stock_code,
                    "title": title[:300],
                    "publish_date": publish_date,
                },
                values={
                    "announcement_type": self._truncate(
                        self._stringify(
                            self._first_value(
                                item,
                                ("announcement_type", "type", "category", "公告类型", "类型"),
                            )
                        ),
                        100,
                    ),
                    "content": content or json.dumps(item, ensure_ascii=False),
                    "source_url": self._truncate(
                        self._stringify(
                            self._first_value(item, ("source_url", "url", "link", "链接", "网址"))
                        ),
                        500,
                    ),
                    "exchange": self._truncate(self._stringify(data.get("exchange")), 20),
                },
            )
            changed = changed or row is not None

        return changed

    def _sync_statement_rows(
        self,
        db: Session,
        data: dict,
        *,
        section: str,
        model,
        field_aliases: dict[str, tuple[str, ...]],
    ) -> bool:
        stock_code = data.get("symbol")
        rows = data.get(section, [])
        if not stock_code or not isinstance(rows, list):
            return False

        changed = False
        for item in rows:
            if not isinstance(item, dict):
                continue

            report_date = self._extract_date(item)
            if report_date is None:
                continue

            values = {
                field: self._to_number(self._first_value(item, aliases))
                for field, aliases in field_aliases.items()
            }

            if any(value is not None for value in values.values()):
                values["source"] = f"company_dataset/{section}"
                row = self._upsert_model(
                    db,
                    model,
                    lookup={"stock_code": stock_code, "report_date": report_date},
                    values=values,
                )
                changed = changed or row is not None

            note = self._upsert_model(
                db,
                FinancialNotes,
                lookup={
                    "stock_code": stock_code,
                    "report_date": report_date,
                    "note_type": section,
                },
                values={
                    "note_json": item,
                    "source": f"company_dataset/{section}",
                },
            )
            changed = changed or note is not None

        return changed

    def _upsert_model(self, db: Session, model, *, lookup: dict, values: dict):
        conditions = [getattr(model, key) == value for key, value in lookup.items()]
        row = db.scalar(select(model).where(*conditions))
        if row is None:
            row = model(**lookup, **values)
            db.add(row)
            db.flush()
        else:
            for key, value in values.items():
                setattr(row, key, value)
        return row

    def _extract_date(self, row: dict) -> date | None:
        raw_value = self._first_value(
            row,
            (
                "report_date",
                "publish_date",
                "notice_date",
                "end_date",
                "date",
                "REPORT_DATE",
                "NOTICE_DATE",
                "报告期",
                "报告日期",
                "报表日期",
                "公告日期",
                "发布时间",
                "日期",
            ),
        )
        return self._to_date(raw_value)

    def _first_value(self, row: dict, aliases: tuple[str, ...]):
        normalized_aliases = {self._normalize_key(alias) for alias in aliases}
        normalized_row = {self._normalize_key(key): value for key, value in row.items()}

        for alias in normalized_aliases:
            if alias in normalized_row and normalized_row[alias] not in (None, ""):
                return normalized_row[alias]

        for key, value in normalized_row.items():
            if value in (None, ""):
                continue
            if any(alias and (alias in key or key in alias) for alias in normalized_aliases):
                return value

        return None

    def _normalize_key(self, value) -> str:
        return re.sub(r"\s+", "", str(value or "")).lower()

    def _stringify(self, value) -> str | None:
        if value in (None, ""):
            return None
        return str(value).strip()

    def _truncate(self, value: str | None, limit: int) -> str | None:
        if value is None:
            return None
        return value[:limit]

    def _to_date(self, value) -> date | None:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if value in (None, ""):
            return None

        text = str(value).strip()
        compact_match = re.search(r"(\d{4})(\d{2})(\d{2})", text)
        if compact_match:
            year, month, day = compact_match.groups()
            try:
                return date(int(year), int(month), int(day))
            except ValueError:
                return None

        date_match = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text)
        if date_match:
            year, month, day = date_match.groups()
            try:
                return date(int(year), int(month), int(day))
            except ValueError:
                return None

        return None

    def _to_number(self, value) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if value in (None, ""):
            return None

        text = str(value).strip().replace(",", "")
        if text in {"-", "--", "None", "nan"}:
            return None
        number_match = re.search(r"-?\d+(?:\.\d+)?", text)
        if number_match is None:
            return None
        try:
            return float(number_match.group(0))
        except ValueError:
            return None

    def _build_financial_records(self, data: dict) -> list[dict]:
        metric_map = {
            "营业总收入": ("营业总收入", "亿元"),
            "净利润": ("净利润", "亿元"),
            "归母净利润": ("归母净利润", "亿元"),
            "扣非净利润": ("扣非净利润", "亿元"),
            "毛利率": ("毛利率", "%"),
            "销售净利率": ("净利率", "%"),
            "净资产收益率(ROE)": ("ROE", "%"),
            "资产负债率": ("资产负债率", "%"),
            "流动比率": ("流动比率", None),
            "速动比率": ("速动比率", None),
            "基本每股收益": ("每股收益", "元"),
            "每股净资产": ("每股净资产", "元"),
            "经营现金流量净额": ("经营现金流量净额", "亿元"),
        }
        amount_metrics = {
            "营业总收入",
            "净利润",
            "归母净利润",
            "扣非净利润",
            "经营现金流量净额",
        }

        records: list[dict] = []
        stock_code = data.get("symbol")
        stock_name = data.get("name") or stock_code
        rows = data.get("financial_abstract", [])

        for row in rows:
            source_metric = row.get("指标")
            if source_metric not in metric_map:
                continue

            target_metric, unit = metric_map[source_metric]
            for period, raw_value in row.items():
                if period in {"选项", "指标"} or raw_value in (None, ""):
                    continue
                if not isinstance(period, str) or len(period) != 8 or not period.endswith("1231"):
                    continue

                try:
                    value = float(raw_value)
                except (TypeError, ValueError):
                    continue

                if source_metric in amount_metrics:
                    value = value / 1e8

                records.append(
                    {
                        "stock_code": stock_code,
                        "stock_name": stock_name,
                        "year": int(period[:4]),
                        "metric_name": target_metric,
                        "metric_value": value,
                        "metric_unit": unit,
                        "source": "company_dataset/financial_abstract",
                    }
                )

        return records