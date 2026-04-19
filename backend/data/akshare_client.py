from __future__ import annotations

from datetime import datetime, timedelta
import random
import time

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
}

NAME_MAPPING = {
    "贵州茅台": "600519",
    "平安银行": "000001",
    "招商银行": "600036",
    "宁德时代": "300750",
    "比亚迪": "002594",
}


class StockDataProvider:
    def __init__(self) -> None:
        self._spot_cache = None
        self._spot_cache_time = 0.0

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
        return {
            "symbol": symbol,
            "name": f"示例股票{symbol}",
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
