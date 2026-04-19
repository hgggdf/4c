from sqlalchemy.orm import Session

from data.company_data_store import CompanyDataStore
from data.akshare_client import StockDataProvider
from data.pharma_company_registry import get_company, list_pharma_companies, resolve_company_symbol
from repository.stock_repo import StockDailyRepository
from repository.user_repo import UserRepository
from repository.watchlist_repo import WatchlistRepository


class StockService:
    def __init__(self) -> None:
        self.provider = StockDataProvider()
        self.company_store = CompanyDataStore()
        self.stock_repo = StockDailyRepository()
        self.user_repo = UserRepository()
        self.watchlist_repo = WatchlistRepository()

    def get_quote(self, symbol: str):
        return self.provider.get_quote(symbol)

    def get_kline(self, db: Session, symbol: str, days: int = 30):
        cached = self.stock_repo.list_recent(db, symbol, days)
        if len(cached) >= days:
            return [
                {
                    "date": row.trade_date.strftime("%Y-%m-%d"),
                    "open": float(row.open),
                    "high": float(row.high),
                    "low": float(row.low),
                    "close": float(row.close),
                    "volume": float(row.volume),
                }
                for row in cached
            ]

        fresh = self.provider.get_kline(symbol, days)
        self.stock_repo.upsert_many(db, symbol, fresh)
        return fresh

    def get_watchlist(self, db: Session, user_id: int):
        user = self.user_repo.get_by_id(db, user_id)
        if user is None:
            user = self.user_repo.get_or_create_demo_user(db)
            user_id = user.id

        rows = self.watchlist_repo.list_by_user(db, user_id)
        if not rows:
            rows = self.watchlist_repo.seed_default(db, user_id)
        return [{"symbol": row.stock_code, "name": row.stock_name or row.stock_code} for row in rows]

    def add_watchlist(self, db: Session, user_id: int, symbol: str, name: str | None):
        user = self.user_repo.get_by_id(db, user_id)
        if user is None:
            user = self.user_repo.get_or_create_demo_user(db)
            user_id = user.id
        row = self.watchlist_repo.add(db, user_id, symbol, name)
        return {"symbol": row.stock_code, "name": row.stock_name or row.stock_code}

    def remove_watchlist(self, db: Session, user_id: int, symbol: str):
        return {"removed": self.watchlist_repo.remove(db, user_id, symbol)}

    def list_pharma_companies(self):
        return self.company_store.list_company_summaries()

    def get_company_dataset(self, symbol: str, refresh: bool = False, compact: bool = True):
        resolved_symbol = resolve_company_symbol(symbol) or symbol
        dataset = None if refresh else self.company_store.load_company_dataset(resolved_symbol, compact=compact)
        if dataset is not None:
            return dataset

        full_dataset = self.provider.collect_company_dataset(resolved_symbol)
        self.company_store.save_company_dataset(full_dataset)
        return self.company_store.to_compact_dataset(full_dataset) if compact else full_dataset

    def refresh_all_company_data(self, compact: bool = True):
        results = []
        for company in list_pharma_companies():
            dataset = self.provider.collect_company_dataset(company["symbol"])
            summary = self.company_store.save_company_dataset(dataset)
            if compact:
                summary["preview"] = self.company_store.to_compact_dataset(dataset)
            results.append(summary)
        return {
            "total": len(results),
            "companies": results,
        }

    def build_company_agent_context(self, symbol: str) -> str:
        dataset = self.get_company_dataset(symbol, refresh=False, compact=True)
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
