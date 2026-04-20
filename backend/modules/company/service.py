"""公司资料聚合服务，负责协调本地文件、数据库缓存和外部数据抓取。"""

from __future__ import annotations

from copy import deepcopy

from sqlalchemy.orm import Session

from external.akshare_client import StockDataProvider
from modules.company.local_store import LocalCompanyDataStore
from modules.company.registry import (
    get_company,
    list_pharma_companies,
    resolve_company_symbol,
)
from core.repositories.company_dataset_repo import CompanyDatasetRepository
from core.repositories.company_dataset_sync_repo import CompanyDatasetSyncRepository


class CompanyService:
    """统一管理公司多源数据的读取、保存、刷新和上下文构建。"""

    def __init__(self) -> None:
        self.provider = StockDataProvider()
        self.local_store = LocalCompanyDataStore()
        self.dataset_repo = CompanyDatasetRepository()
        self.dataset_sync_repo = CompanyDatasetSyncRepository()

    def load_company_dataset(
        self,
        db: Session,
        symbol: str,
        *,
        compact: bool = False,
    ) -> dict | None:
        """优先从数据库读取公司资料，未命中时回退到本地文件并同步入库。"""
        row = self.dataset_repo.get_by_symbol(db, symbol)
        if row is not None:
            return deepcopy(row.compact_json if compact else row.dataset_json)

        data = self.local_store.load_company_dataset(symbol)
        if data is None:
            return None

        self.save_company_dataset(db, data)
        return self.local_store.to_compact_dataset(data) if compact else data

    def save_company_dataset(self, db: Session, data: dict) -> dict:
        """把公司聚合资料同时写入本地文件、数据库摘要表和结构化明细表。"""
        summary = self.local_store.save_company_dataset(data)
        self.dataset_repo.upsert(
            db,
            symbol=data["symbol"],
            name=summary["name"],
            exchange=summary.get("exchange"),
            collected_at=summary.get("collected_at"),
            summary_json=summary,
            compact_json=self.local_store.to_compact_dataset(data),
            dataset_json=data,
            commit=False,
        )
        self.dataset_sync_repo.sync_financial_data(db, data)
        self.dataset_sync_repo.sync_structured_dataset(db, data)
        db.commit()
        return summary

    def list_company_summaries(self, db: Session) -> list[dict]:
        """合并本地索引与数据库摘要，返回完整的公司概览列表。"""
        local_rows = {
            row["symbol"]: deepcopy(row) for row in self.local_store.list_company_summaries()
        }
        db_rows = {
            row["symbol"]: deepcopy(row["summary_json"])
            for row in self.dataset_repo.list_summaries(db)
        }

        results: list[dict] = []
        for company in list_pharma_companies():
            symbol = company["symbol"]
            summary = deepcopy(local_rows.get(symbol, {}))
            summary.update(deepcopy(db_rows.get(symbol, {})))
            summary.setdefault("symbol", symbol)
            summary.setdefault("name", company["name"])
            summary.setdefault("exchange", company["exchange"])
            summary.setdefault("aliases", company.get("aliases", []))
            summary["has_local_data"] = bool(local_rows.get(symbol) or db_rows.get(symbol))
            results.append(summary)
        return results

    def get_company_dataset(
        self,
        db: Session,
        symbol: str,
        *,
        refresh: bool = False,
        compact: bool = True,
    ) -> dict:
        """按股票代码或名称获取公司聚合资料，并支持按需刷新。"""
        resolved_symbol = resolve_company_symbol(symbol) or symbol
        dataset = None
        if not refresh:
            dataset = self.load_company_dataset(db, resolved_symbol, compact=compact)
        if dataset is not None:
            return dataset

        full_dataset = self.provider.collect_company_dataset(resolved_symbol)
        self.save_company_dataset(db, full_dataset)
        return self.local_store.to_compact_dataset(full_dataset) if compact else full_dataset

    def refresh_all_company_data(self, db: Session, *, compact: bool = True) -> dict:
        """批量刷新观察池中全部公司的聚合资料。"""
        results = []
        for company in list_pharma_companies():
            dataset = self.provider.collect_company_dataset(company["symbol"])
            summary = self.save_company_dataset(db, dataset)
            if compact:
                summary["preview"] = self.local_store.to_compact_dataset(dataset)
            results.append(summary)

        return {"total": len(results), "companies": results}

    def bootstrap_from_local_files(self, db: Session) -> dict:
        """把已有的本地 dataset.json 批量导入数据库摘要表。"""
        imported = 0
        skipped = 0
        existing_symbols = set(self.dataset_repo.list_symbols(db))

        for dataset_file in self.local_store.list_dataset_files():
            try:
                data = self.local_store.load_dataset_file(dataset_file)
            except Exception:
                skipped += 1
                continue

            symbol = data.get("symbol")
            if not symbol or symbol in existing_symbols:
                skipped += 1
                continue

            self.save_company_dataset(db, data)
            existing_symbols.add(symbol)
            imported += 1

        return {"imported": imported, "skipped": skipped}

    def backfill_structured_tables_from_local_files(self, db: Session) -> dict:
        """根据本地 dataset.json 回填结构化财务表和公告表。"""
        imported = 0
        skipped = 0

        for dataset_file in self.local_store.list_dataset_files():
            try:
                data = self.local_store.load_dataset_file(dataset_file)
            except Exception:
                skipped += 1
                continue

            if not data.get("symbol"):
                skipped += 1
                continue

            self.dataset_sync_repo.sync_financial_data(db, data)
            self.dataset_sync_repo.sync_structured_dataset(db, data)
            db.commit()
            imported += 1

        return {"imported": imported, "skipped": skipped}

    def build_company_agent_context(self, db: Session, symbol: str) -> str:
        """为智能体拼装单家公司可直接消费的文本上下文。"""
        dataset = self.get_company_dataset(db, symbol, refresh=False, compact=True)
        company = get_company(symbol) or {"name": dataset.get("name", symbol)}
        parts: list[str] = []

        info = dataset.get("company_info", {})
        if info:
            parts.append(
                "【公司档案】"
                f"{company['name']}（{symbol}），行业：{info.get('行业', '未知')}，"
                f"总市值：{info.get('总市值', '未知')}，流通市值：{info.get('流通市值', '未知')}，"
                f"上市时间：{info.get('上市时间', '未知')}"
            )

        financial_abstract = dataset.get("financial_abstract", [])
        key_metrics = []
        wanted_metrics = {"归母净利润", "营业总收入", "扣非净利润", "净资产收益率", "毛利率"}
        for row in financial_abstract:
            metric_name = row.get("指标")
            if metric_name in wanted_metrics:
                latest_pairs = [
                    (key, value)
                    for key, value in row.items()
                    if key not in {"选项", "指标"} and value not in (None, "")
                ]
                if latest_pairs:
                    latest_key, latest_value = latest_pairs[0]
                    key_metrics.append(f"{metric_name}（{latest_key}）：{latest_value}")
            if len(key_metrics) >= 5:
                break
        if key_metrics:
            parts.append("【财务摘要】" + "；".join(key_metrics))

        main_business = dataset.get("main_business", [])[:5]
        if main_business:
            lines = []
            for row in main_business:
                lines.append(
                    f"{row.get('分类类型', '')} - {row.get('主营构成', '')}：收入 {row.get('主营收入', '')}，毛利率 {row.get('毛利率', '')}"
                )
            parts.append("【主营构成】" + "；".join(lines))

        report_lines = []
        for item in dataset.get("research_reports", [])[:3]:
            report_lines.append(
                f"[{item.get('日期', '')}] {item.get('报告名称', '')}（{item.get('机构', '')}，评级 {item.get('东财评级', '')}）"
            )
        if report_lines:
            parts.append("【最新研报】\n" + "\n".join(report_lines))

        announcement_lines = []
        for item in dataset.get("announcements", [])[:5]:
            announcement_lines.append(
                f"[{item.get('公告日期', '')}] {item.get('公告标题', '')}（{item.get('公告类型', '')}）"
            )
        if announcement_lines:
            parts.append("【最新公告】\n" + "\n".join(announcement_lines))

        news_lines = []
        for item in dataset.get("news", [])[:3]:
            news_lines.append(
                f"[{item.get('发布时间', '')}] {item.get('新闻标题', '')}（{item.get('文章来源', '')}）"
            )
        if news_lines:
            parts.append("【相关新闻】\n" + "\n".join(news_lines))

        return "\n\n".join(parts)