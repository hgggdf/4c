from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from sqlalchemy.orm import Session

from database.session import engine
from data.pharma_company_registry import get_company, list_pharma_companies
from repository.company_dataset_repo import CompanyDatasetRepository
from repository.financial_repo import FinancialDataRepository


STORE_ROOT = Path(__file__).parent.parent / "local_data" / "pharma_companies"
INDEX_FILE = STORE_ROOT / "index.json"

HEAVY_SECTIONS = {
    "financial_abstract": 12,
    "financial_indicators": 12,
    "balance_sheet": 10,
    "profit_sheet": 10,
    "cash_flow_sheet": 10,
    "fund_flow": 30,
    "research_reports": 12,
    "announcements": 20,
    "news": 12,
    "main_business": 20,
    "industry_reports": 12,
}


class CompanyDataStore:
    def __init__(self) -> None:
        STORE_ROOT.mkdir(parents=True, exist_ok=True)
        self.repo = CompanyDatasetRepository()
        self.financial_repo = FinancialDataRepository()

    def _company_dir(self, symbol: str) -> Path:
        return STORE_ROOT / symbol

    def _dataset_file(self, symbol: str) -> Path:
        return self._company_dir(symbol) / "dataset.json"

    def load_company_dataset(self, symbol: str, compact: bool = False) -> dict | None:
        with Session(engine) as db:
            row = self.repo.get_by_symbol(db, symbol)
            if row is not None:
                return deepcopy(row.compact_json if compact else row.dataset_json)

        data = self._load_local_dataset(symbol)
        if data is None:
            return None

        self.save_company_dataset(data)
        return self.to_compact_dataset(data) if compact else data

    def save_company_dataset(self, data: dict) -> dict:
        summary = self._build_index_entry(data)

        with Session(engine) as db:
            self.repo.upsert(
                db,
                symbol=data["symbol"],
                name=summary["name"],
                exchange=summary.get("exchange"),
                collected_at=summary.get("collected_at"),
                summary_json=summary,
                compact_json=self.to_compact_dataset(data),
                dataset_json=data,
            )
            self._sync_financial_data(db, data)

        return summary

    def list_company_summaries(self) -> list[dict]:
        with Session(engine) as db:
            db_rows = {
                row["symbol"]: deepcopy(row["summary_json"])
                for row in self.repo.list_summaries(db)
            }

        results: list[dict] = []
        for company in list_pharma_companies():
            summary = deepcopy(db_rows.get(company["symbol"], {}))
            summary.setdefault("symbol", company["symbol"])
            summary.setdefault("name", company["name"])
            summary.setdefault("exchange", company["exchange"])
            summary.setdefault("aliases", company.get("aliases", []))
            summary.setdefault("has_local_data", bool(db_rows.get(company["symbol"])))
            results.append(summary)
        return results

    def bootstrap_from_local_files(self) -> dict:
        imported = 0
        skipped = 0

        dataset_files = sorted(STORE_ROOT.glob("*/dataset.json"))
        if not dataset_files:
            return {"imported": 0, "skipped": 0}

        with Session(engine) as db:
            existing_symbols = set(self.repo.list_symbols(db))

        for dataset_file in dataset_files:
            try:
                data = json.loads(dataset_file.read_text(encoding="utf-8"))
            except Exception:
                skipped += 1
                continue

            symbol = data.get("symbol")
            if not symbol:
                skipped += 1
                continue

            if symbol in existing_symbols:
                skipped += 1
                continue

            self.save_company_dataset(data)
            existing_symbols.add(symbol)
            imported += 1

        return {"imported": imported, "skipped": skipped}

    def to_compact_dataset(self, data: dict) -> dict:
        compact = deepcopy(data)
        for section, limit in HEAVY_SECTIONS.items():
            value = compact.get(section)
            if isinstance(value, list):
                compact[section] = value[:limit]
        return compact

    def _load_index(self) -> dict[str, dict]:
        if not INDEX_FILE.exists():
            return {}
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))

    def _load_local_dataset(self, symbol: str) -> dict | None:
        dataset_file = self._dataset_file(symbol)
        if not dataset_file.exists():
            return None
        return json.loads(dataset_file.read_text(encoding="utf-8"))

    def _sync_financial_data(self, db: Session, data: dict) -> None:
        records = self._build_financial_records(data)
        if records:
            self.financial_repo.batch_upsert(db, records)

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

    def _build_index_entry(self, data: dict) -> dict:
        company = get_company(data["symbol"]) or {}
        source_status = data.get("source_status", {})
        return {
            "symbol": data["symbol"],
            "name": data.get("name") or company.get("name") or data["symbol"],
            "exchange": data.get("exchange") or company.get("exchange"),
            "aliases": company.get("aliases", []),
            "collected_at": data.get("collected_at"),
            "has_local_data": True,
            "available_sections": [
                key for key, value in data.items()
                if key not in {"source_status"} and value not in (None, [], {}, "")
            ],
            "source_status": source_status,
            "quote": data.get("quote"),
        }