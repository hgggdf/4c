"""Tushare 客户端封装，负责按股票代码抓取基础面数据。"""

from __future__ import annotations

from datetime import datetime

from config import get_settings
from app.data.pharma_company_registry import to_tushare_code

try:
    import tushare as ts
except Exception:
    ts = None


class TushareClient:
    """对 tushare.pro 的轻量包装，屏蔽令牌初始化和异常处理细节。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._pro = None

    def available(self) -> bool:
        return ts is not None and bool(self.settings.tushare_token.strip())

    def get_pro(self):
        if not self.available():
            return None
        if self._pro is None:
            ts.set_token(self.settings.tushare_token.strip())
            self._pro = ts.pro_api()
        return self._pro

    def collect_company_data(self, symbol: str) -> tuple[dict, dict]:
        source_status: dict[str, dict] = {}
        if not self.available():
            reason = "未配置 tushare 或未安装 tushare 包"
            source_status["tushare_daily_basic"] = {
                "ok": False,
                "source": "tushare.daily_basic",
                "error": reason,
            }
            source_status["tushare_fina_indicator"] = {
                "ok": False,
                "source": "tushare.fina_indicator",
                "error": reason,
            }
            return {"daily_basic": [], "fina_indicator": []}, source_status

        pro = self.get_pro()
        ts_code = to_tushare_code(symbol)
        today = datetime.now().strftime("%Y%m%d")

        result = {"daily_basic": [], "fina_indicator": []}

        try:
            daily_basic_df = pro.daily_basic(
                ts_code=ts_code,
                start_date="20200101",
                end_date=today,
            )
            result["daily_basic"] = daily_basic_df.fillna("").to_dict(orient="records")
            source_status["tushare_daily_basic"] = {
                "ok": True,
                "source": "tushare.daily_basic",
                "count": len(result["daily_basic"]),
            }
        except Exception as exc:
            source_status["tushare_daily_basic"] = {
                "ok": False,
                "source": "tushare.daily_basic",
                "error": str(exc),
            }

        try:
            fina_indicator_df = pro.fina_indicator(ts_code=ts_code)
            result["fina_indicator"] = fina_indicator_df.fillna("").to_dict(orient="records")
            source_status["tushare_fina_indicator"] = {
                "ok": True,
                "source": "tushare.fina_indicator",
                "count": len(result["fina_indicator"]),
            }
        except Exception as exc:
            source_status["tushare_fina_indicator"] = {
                "ok": False,
                "source": "tushare.fina_indicator",
                "error": str(exc),
            }

        return result, source_status
