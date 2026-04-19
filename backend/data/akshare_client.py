from __future__ import annotations

from datetime import date, datetime, timedelta
import math
import os
import random
import time

from config import get_settings
from data.pharma_company_registry import get_company, list_pharma_companies, resolve_company_symbol, to_market_prefix
from data.tushare_client import TushareClient
from data.web_scraper import fetch_pharma_news

try:
    import akshare as ak
except Exception:
    ak = None


MOCK_QUOTES = {
    "600519": {"symbol": "600519", "name": "贵州茅台", "price": 1688.88, "change": 12.36, "change_percent": 0.74, "open": 1673.52, "high": 1699.80, "low": 1668.00, "volume": "2.31万手", "time": "15:00:00"},
    "000001": {"symbol": "000001", "name": "平安银行", "price": 10.82, "change": -0.08, "change_percent": -0.73, "open": 10.90, "high": 10.96, "low": 10.76, "volume": "91.24万手", "time": "15:00:00"},
    "600036": {"symbol": "600036", "name": "招商银行", "price": 34.57, "change": 0.21, "change_percent": 0.61, "open": 34.26, "high": 34.74, "low": 34.11, "volume": "24.61万手", "time": "15:00:00"},
    "300750": {"symbol": "300750", "name": "宁德时代", "price": 191.62, "change": 1.54, "change_percent": 0.81, "open": 189.90, "high": 193.40, "low": 188.75, "volume": "18.05万手", "time": "15:00:00"},
    "002594": {"symbol": "002594", "name": "比亚迪", "price": 242.13, "change": -2.16, "change_percent": -0.88, "open": 244.00, "high": 245.28, "low": 240.86, "volume": "15.70万手", "time": "15:00:00"},
    "000002": {"symbol": "000002", "name": "万科A", "price": 7.35, "change": -0.12, "change_percent": -1.61, "open": 7.48, "high": 7.52, "low": 7.30, "volume": "55.30万手", "time": "15:00:00"},
    "600000": {"symbol": "600000", "name": "浦发银行", "price": 8.92, "change": 0.05, "change_percent": 0.56, "open": 8.87, "high": 8.96, "low": 8.85, "volume": "30.12万手", "time": "15:00:00"},
    "601318": {"symbol": "601318", "name": "中国平安", "price": 52.30, "change": 0.68, "change_percent": 1.32, "open": 51.60, "high": 52.55, "low": 51.40, "volume": "40.88万手", "time": "15:00:00"},
    "600276": {"symbol": "600276", "name": "恒瑞医药", "price": 38.45, "change": -0.55, "change_percent": -1.41, "open": 39.00, "high": 39.20, "low": 38.30, "volume": "22.67万手", "time": "15:00:00"},
    "300015": {"symbol": "300015", "name": "爱尔眼科", "price": 11.28, "change": 0.18, "change_percent": 1.62, "open": 11.10, "high": 11.35, "low": 11.05, "volume": "18.44万手", "time": "15:00:00"},
    "603259": {"symbol": "603259", "name": "药明康德", "price": 58.20, "change": -1.10, "change_percent": -1.85, "open": 59.30, "high": 59.50, "low": 57.90, "volume": "35.21万手", "time": "15:00:00"},
    "688599": {"symbol": "688599", "name": "天合光能", "price": 8.15, "change": 0.22, "change_percent": 2.78, "open": 7.93, "high": 8.20, "low": 7.88, "volume": "28.90万手", "time": "15:00:00"},
}

NAME_MAPPING = {
    "贵州茅台": "600519",
    "平安银行": "000001",
    "招商银行": "600036",
    "宁德时代": "300750",
    "比亚迪": "002594",
    "万科": "000002",
    "万科A": "000002",
    "浦发银行": "600000",
    "中国平安": "601318",
    "天合光能": "688599",
}

for company in list_pharma_companies():
    NAME_MAPPING[company["name"]] = company["symbol"]
    for alias in company.get("aliases", []):
        NAME_MAPPING[alias] = company["symbol"]


class StockDataProvider:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._spot_cache = None
        self._spot_cache_time = 0.0
        self.tushare_client = TushareClient()
        self._sanitize_proxy_env()

    def _sanitize_proxy_env(self) -> None:
        for key in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
            if key in os.environ:
                os.environ[key] = ""

    def _get_spot_df_cached(self):
        if ak is None:
            return None
        now = time.time()
        if self._spot_cache is not None and now - self._spot_cache_time < 60:
            return self._spot_cache

        try:
            self._spot_cache = ak.stock_zh_a_spot_em()
            self._spot_cache_time = now
            return self._spot_cache
        except Exception:
            return None

    def resolve_symbol(self, message: str) -> str | None:
        resolved = resolve_company_symbol(message)
        if resolved:
            return resolved
        for name, symbol in NAME_MAPPING.items():
            if name in message:
                return symbol
        return None

    def get_quote(self, symbol: str) -> dict:
        spot_df = self._get_spot_df_cached()
        if spot_df is not None:
            try:
                row = spot_df[spot_df["代码"] == symbol]
                if not row.empty:
                    item = row.iloc[0]
                    return {
                        "symbol": symbol,
                        "name": item.get("名称", symbol),
                        "price": float(item.get("最新价", 0) or 0),
                        "change": float(item.get("涨跌额", 0) or 0),
                        "change_percent": float(item.get("涨跌幅", 0) or 0),
                        "open": float(item.get("今开", 0) or 0),
                        "high": float(item.get("最高", 0) or 0),
                        "low": float(item.get("最低", 0) or 0),
                        "volume": f"{float(item.get('成交量', 0) or 0):,.0f}",
                        "time": datetime.now().strftime("%H:%M:%S"),
                    }
            except Exception:
                pass

        info_map = self.get_company_info(symbol)
        if info_map:
            company = get_company(symbol)
            latest = self._to_float(info_map.get("最新"))
            return {
                "symbol": symbol,
                "name": info_map.get("股票简称") or (company.get("name") if company else symbol),
                "price": latest,
                "change": 0.0,
                "change_percent": 0.0,
                "open": latest,
                "high": latest,
                "low": latest,
                "volume": str(info_map.get("流通股") or "0"),
                "time": datetime.now().strftime("%H:%M:%S"),
            }

        return MOCK_QUOTES.get(symbol, self._build_fallback_quote(symbol))

    def get_kline(self, symbol: str, days: int = 30) -> list[dict]:
        if ak is not None:
            try:
                end_date = datetime.now().strftime("%Y%m%d")
                start_date = (datetime.now() - timedelta(days=days * 3)).strftime("%Y%m%d")
                hist_df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="",
                )
                if hist_df is not None and not hist_df.empty:
                    hist_df = hist_df.tail(days)
                    result = []
                    for _, row in hist_df.iterrows():
                        result.append(
                            {
                                "date": str(row["日期"]),
                                "open": float(row["开盘"]),
                                "high": float(row["最高"]),
                                "low": float(row["最低"]),
                                "close": float(row["收盘"]),
                                "volume": float(row["成交量"]),
                            }
                        )
                    if result:
                        return result
            except Exception:
                pass

        return self._build_mock_kline(symbol, days)

    def _build_fallback_quote(self, symbol: str) -> dict:
        company = get_company(symbol)
        return {
            "symbol": symbol,
            "name": company["name"] if company else f"示例股票{symbol}",
            "price": 20.16,
            "change": 0.32,
            "change_percent": 1.61,
            "open": 19.91,
            "high": 20.33,
            "low": 19.70,
            "volume": "8.35万手",
            "time": "15:00:00",
        }

    def _build_mock_kline(self, symbol: str, days: int) -> list[dict]:
        base = self.get_quote(symbol)["price"]
        data = []
        current = round(float(base), 2)

        for offset in range(days):
            date = (datetime.now() - timedelta(days=days - offset - 1)).strftime("%Y-%m-%d")
            drift = random.uniform(-1.8, 1.8)
            open_price = round(current + random.uniform(-1, 1), 2)
            close_price = round(max(1, open_price + drift), 2)
            high_price = round(max(open_price, close_price) + random.uniform(0, 1.2), 2)
            low_price = round(min(open_price, close_price) - random.uniform(0, 1.2), 2)
            volume = round(random.uniform(10000, 50000), 2)

            data.append(
                {
                    "date": date,
                    "open": open_price,
                    "high": high_price,
                    "low": max(0.01, low_price),
                    "close": close_price,
                    "volume": volume,
                }
            )
            current = close_price

        return data

    def get_company_info(self, symbol: str) -> dict:
        records, _ = self._safe_ak_call("stock_individual_info_em", symbol=symbol)
        info = {}
        for item in records:
            key = item.get("item")
            if key:
                info[str(key)] = item.get("value")
        return info

    def collect_company_dataset(self, symbol: str, history_days: int = 180) -> dict:
        company = get_company(symbol) or {
            "symbol": symbol,
            "name": symbol,
            "exchange": to_market_prefix(symbol),
            "aliases": [],
        }
        market_prefix = to_market_prefix(symbol)
        market_lower = market_prefix.lower()
        em_symbol = f"{market_prefix}{symbol}"

        source_status: dict[str, dict] = {}

        company_info_records, source_status["company_info"] = self._safe_ak_call(
            "stock_individual_info_em",
            symbol=symbol,
        )
        company_info = {
            str(item.get("item")): item.get("value")
            for item in company_info_records
            if item.get("item")
        }

        financial_abstract, source_status["financial_abstract"] = self._safe_ak_call(
            "stock_financial_abstract",
            symbol=symbol,
        )

        financial_indicators, source_status["financial_indicators"] = self._safe_ak_call_any(
            [
                ("stock_financial_analysis_indicator", {"symbol": symbol}),
                ("stock_financial_analysis_indicator_em", {"symbol": em_symbol, "indicator": "按报告期"}),
            ]
        )

        main_business, source_status["main_business"] = self._safe_ak_call(
            "stock_zygc_em",
            symbol=em_symbol,
        )

        research_reports, source_status["research_reports"] = self._safe_ak_call(
            "stock_research_report_em",
            symbol=symbol,
        )

        announcements, source_status["announcements"] = self._safe_ak_call(
            "stock_individual_notice_report",
            security=symbol,
            symbol="全部",
            begin_date="20200101",
            end_date=datetime.now().strftime("%Y%m%d"),
        )

        news, source_status["news"] = self._safe_ak_call(
            "stock_news_em",
            symbol=symbol,
        )

        fund_flow, source_status["fund_flow"] = self._safe_ak_call(
            "stock_individual_fund_flow",
            stock=symbol,
            market=market_lower,
        )

        balance_sheet, source_status["balance_sheet"] = self._safe_ak_call(
            "stock_balance_sheet_by_report_em",
            symbol=em_symbol,
        )

        profit_sheet, source_status["profit_sheet"] = self._safe_ak_call(
            "stock_profit_sheet_by_report_em",
            symbol=em_symbol,
        )

        cash_flow_sheet, source_status["cash_flow_sheet"] = self._safe_ak_call(
            "stock_cash_flow_sheet_by_report_em",
            symbol=em_symbol,
        )

        try:
            company_reports = fetch_pharma_news(symbol)
            source_status["web_scraper_stock_reports"] = {
                "ok": True,
                "source": "web_scraper.fetch_pharma_news(symbol)",
                "count": len(company_reports),
            }
        except Exception as exc:
            company_reports = []
            source_status["web_scraper_stock_reports"] = {
                "ok": False,
                "source": "web_scraper.fetch_pharma_news(symbol)",
                "error": str(exc),
            }

        try:
            industry_reports = fetch_pharma_news(None)
            source_status["web_scraper_industry_reports"] = {
                "ok": True,
                "source": "web_scraper.fetch_pharma_news(None)",
                "count": len(industry_reports),
            }
        except Exception as exc:
            industry_reports = []
            source_status["web_scraper_industry_reports"] = {
                "ok": False,
                "source": "web_scraper.fetch_pharma_news(None)",
                "error": str(exc),
            }

        tushare_data, tushare_status = self.tushare_client.collect_company_data(symbol)
        source_status.update(tushare_status)

        quote = self.get_quote(symbol)
        kline = self.get_kline(symbol, history_days)

        return {
            "symbol": symbol,
            "name": company.get("name") or quote.get("name") or symbol,
            "exchange": company.get("exchange") or market_prefix,
            "aliases": company.get("aliases", []),
            "collected_at": datetime.now().isoformat(timespec="seconds"),
            "quote": quote,
            "kline": kline,
            "company_info": company_info,
            "financial_abstract": financial_abstract,
            "financial_indicators": financial_indicators,
            "main_business": main_business,
            "research_reports": research_reports,
            "announcements": announcements,
            "news": news,
            "fund_flow": fund_flow,
            "balance_sheet": balance_sheet,
            "profit_sheet": profit_sheet,
            "cash_flow_sheet": cash_flow_sheet,
            "stock_reports": company_reports,
            "industry_reports": industry_reports,
            "tushare": tushare_data,
            "source_status": source_status,
        }

    def _safe_ak_call(self, func_name: str, **kwargs) -> tuple[list[dict], dict]:
        if ak is None:
            return [], {"ok": False, "source": func_name, "error": "akshare 不可用"}
        func = getattr(ak, func_name, None)
        if func is None:
            return [], {"ok": False, "source": func_name, "error": "接口不存在"}
        try:
            df = func(**kwargs)
            records = self._df_to_records(df)
            return records, {"ok": True, "source": func_name, "count": len(records)}
        except Exception as exc:
            return [], {"ok": False, "source": func_name, "error": str(exc)}

    def _safe_ak_call_any(self, candidates: list[tuple[str, dict]]) -> tuple[list[dict], dict]:
        errors = []
        for func_name, kwargs in candidates:
            records, status = self._safe_ak_call(func_name, **kwargs)
            if status.get("ok"):
                return records, status
            errors.append(f"{func_name}: {status.get('error')}")
        return [], {"ok": False, "source": ", ".join(name for name, _ in candidates), "error": " | ".join(errors)}

    def _df_to_records(self, df) -> list[dict]:
        if df is None or getattr(df, "empty", True):
            return []
        records = []
        for item in df.to_dict(orient="records"):
            row = {}
            for key, value in item.items():
                normalized_key = str(key).strip()
                row[normalized_key] = self._normalize_value(value)
            records.append(row)
        return records

    def _normalize_value(self, value):
        if value is None:
            return None
        if hasattr(value, "item"):
            try:
                value = value.item()
            except Exception:
                pass
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, float) and math.isnan(value):
            return None
        return value

    def _to_float(self, value) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0
