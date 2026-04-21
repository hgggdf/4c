"""抓取客户端。"""

from .akshare_client import StockDataProvider
from .tushare_client import TushareClient

__all__ = ["StockDataProvider", "TushareClient"]