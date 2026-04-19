import re

from data.akshare_client import StockDataProvider
from data.web_scraper import fetch_pharma_news
from data.pdf_parser import extract_financial_highlights


class AgentTools:
    def __init__(self) -> None:
        self.provider = StockDataProvider()

    def extract_symbol(self, message: str) -> str | None:
        code_match = re.search(r"\b(\d{6})\b", message)
        if code_match:
            return code_match.group(1)
        return self.provider.resolve_symbol(message)

    def get_quote(self, symbol: str) -> dict:
        return self.provider.get_quote(symbol)

    def get_pharma_news(self, symbol: str | None = None) -> list[dict]:
        """获取医药行业资讯或个股研报"""
        try:
            return fetch_pharma_news(symbol)
        except Exception as e:
            return [{"error": str(e), "source": "资讯抓取"}]

    def analyze_financial_data(self, text: str) -> dict:
        """从年报文本提取财务指标"""
        try:
            return extract_financial_highlights(text)
        except Exception as e:
            return {"error": str(e)}
