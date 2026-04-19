"""
网页爬虫工具：从东方财富、上交所、深交所等抓取医药行业数据
"""
from __future__ import annotations

import re
import time
import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def _get(url: str, timeout: int = 15, params: dict | None = None) -> requests.Response:
    resp = requests.get(url, headers=HEADERS, timeout=timeout, params=params)
    resp.raise_for_status()
    return resp


def fetch_eastmoney_industry_reports(keyword: str = "医药", limit: int = 5) -> list[dict]:
    """从东方财富爬取行业研报摘要"""
    url = "https://data.eastmoney.com/report/industry.jshtml"
    try:
        resp = _get(url)
        soup = BeautifulSoup(resp.text, "lxml")
        results = []
        rows = soup.select("table.tab1 tr")[1:limit + 1]
        for row in rows:
            cols = row.select("td")
            if len(cols) >= 4:
                title_tag = cols[0].find("a")
                title = title_tag.get_text(strip=True) if title_tag else ""
                org = cols[1].get_text(strip=True)
                date = cols[2].get_text(strip=True)
                if keyword in title or not keyword:
                    results.append({"title": title, "org": org, "date": date, "source": "东方财富研报"})
        return results
    except Exception as e:
        return [{"error": str(e), "source": "东方财富研报"}]


def fetch_eastmoney_stock_reports(symbol: str, limit: int = 3) -> list[dict]:
    """从东方财富爬取个股研报摘要"""
    url = "https://data.eastmoney.com/report/stock.jshtml"
    try:
        resp = _get(url, params={"code": symbol})
        soup = BeautifulSoup(resp.text, "lxml")
        results = []
        rows = soup.select("table.tab1 tr")[1:limit + 1]
        for row in rows:
            cols = row.select("td")
            if len(cols) >= 4:
                title_tag = cols[0].find("a")
                title = title_tag.get_text(strip=True) if title_tag else ""
                org = cols[1].get_text(strip=True)
                date = cols[2].get_text(strip=True)
                results.append({"title": title, "org": org, "date": date, "source": "东方财富个股研报"})
        return results
    except Exception as e:
        return [{"error": str(e), "source": "东方财富个股研报"}]


def fetch_sse_announcements(keyword: str = "医药", limit: int = 5) -> list[dict]:
    """从上交所爬取公告列表"""
    url = "https://www.sse.com.cn/disclosure/listedinfo/regular/"
    try:
        resp = _get(url)
        soup = BeautifulSoup(resp.text, "lxml")
        results = []
        links = soup.select("a[href*='announcement']")[:limit]
        for a in links:
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if keyword in title or not keyword:
                results.append({"title": title, "url": href, "source": "上交所公告"})
        return results
    except Exception as e:
        return [{"error": str(e), "source": "上交所公告"}]


def fetch_pharma_news(symbol: str | None = None) -> list[dict]:
    """
    综合抓取医药相关资讯：
    - 有 symbol 时抓个股研报
    - 无 symbol 时抓行业研报
    """
    if symbol:
        return fetch_eastmoney_stock_reports(symbol)
    return fetch_eastmoney_industry_reports(keyword="医药")
