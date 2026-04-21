"""本地公司数据文件仓库，负责 dataset.json 与索引文件的读写。"""

from __future__ import annotations

import json
from copy import deepcopy

from app.paths import PHARMA_COMPANIES_DATA_DIR
from crawler.reference.pharma_company_registry import get_company, list_pharma_companies


STORE_ROOT = PHARMA_COMPANIES_DATA_DIR
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


class LocalCompanyDataStore:
    """管理 backend/local_data/pharma_companies 下的本地 JSON 数据集。"""

    def __init__(self) -> None:
        STORE_ROOT.mkdir(parents=True, exist_ok=True)

    def list_dataset_files(self) -> list[Path]:
        return sorted(STORE_ROOT.glob("*/dataset.json"))

    def load_company_dataset(self, symbol: str) -> dict | None:
        dataset_file = self._dataset_file(symbol)
        if not dataset_file.exists():
            return None
        return json.loads(dataset_file.read_text(encoding="utf-8"))

    def load_dataset_file(self, dataset_file: Path) -> dict:
        return json.loads(dataset_file.read_text(encoding="utf-8"))

    def save_company_dataset(self, data: dict) -> dict:
        symbol = data["symbol"]
        company_dir = self._company_dir(symbol)
        company_dir.mkdir(parents=True, exist_ok=True)

        dataset_file = self._dataset_file(symbol)
        dataset_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        summary = self.build_index_entry(data)
        index = self._load_index()
        index[symbol] = summary
        INDEX_FILE.write_text(
            json.dumps(index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return summary

    def list_company_summaries(self) -> list[dict]:
        index = self._load_index()
        results: list[dict] = []
        for company in list_pharma_companies():
            summary = deepcopy(index.get(company["symbol"], {}))
            summary.setdefault("symbol", company["symbol"])
            summary.setdefault("name", company["name"])
            summary.setdefault("exchange", company["exchange"])
            summary.setdefault("aliases", company.get("aliases", []))
            summary.setdefault("has_local_data", bool(index.get(company["symbol"])))
            results.append(summary)
        return results

    def to_compact_dataset(self, data: dict) -> dict:
        compact = deepcopy(data)
        for section, limit in HEAVY_SECTIONS.items():
            value = compact.get(section)
            if isinstance(value, list):
                compact[section] = value[:limit]
        return compact

    def build_index_entry(self, data: dict) -> dict:
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
                key
                for key, value in data.items()
                if key not in {"source_status"} and value not in (None, [], {}, "")
            ],
            "source_status": source_status,
            "quote": data.get("quote"),
        }

    def _load_index(self) -> dict[str, dict]:
        if not INDEX_FILE.exists():
            return {}
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))

    def _company_dir(self, symbol: str) -> Path:
        return STORE_ROOT / symbol

    def _dataset_file(self, symbol: str) -> Path:
        return self._company_dir(symbol) / "dataset.json"