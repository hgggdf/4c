from __future__ import annotations

from datetime import datetime
import hashlib
import json
import math
from typing import Any

from bs4 import BeautifulSoup

from .http_client import (
    CrawlerRuntimeConfig,
    CrawlRequestError,
    SiteHttpClient,
    build_crawl_result,
    load_sample_json,
)


def _normalize_stock_code(value: str | None) -> str | None:
    digits = "".join(ch for ch in str(value or "").strip() if ch.isdigit())
    if len(digits) >= 6:
        return digits[-6:]
    return digits or None


def _normalize_date(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(text[:19], fmt).date().isoformat()
        except ValueError:
            continue
    text = text.replace("/", "-").replace(".", "-")
    if len(text) >= 10:
        return text[:10]
    return None


def _infer_exchange(stock_code: str | None) -> str | None:
    code = str(stock_code or "")
    if code.startswith(("60", "68", "90")):
        return "SSE"
    if code.startswith(("00", "20", "30")):
        return "SZSE"
    if code.startswith(("43", "83", "87", "92")):
        return "BSE"
    return None


def _json_detail_url(stock_code: str | None, info_code: str | None) -> str | None:
    normalized = _normalize_stock_code(stock_code)
    info = str(info_code or "").strip()
    if not normalized or not info:
        return None
    return f"https://data.eastmoney.com/notices/detail/{normalized}/{info}.html"


class EastmoneyClient:
    def __init__(self, *, config: CrawlerRuntimeConfig | None = None) -> None:
        self.config = config or CrawlerRuntimeConfig.from_settings()
        self.http = SiteHttpClient("eastmoney", config=self.config)

    def fetch_stock_reports(
        self,
        stock_code: str,
        *,
        limit: int = 20,
        strategy: str = "auto",
        source_mode: str | None = None,
    ) -> dict:
        normalized_stock_code = _normalize_stock_code(stock_code)
        if not normalized_stock_code:
            return build_crawl_result(
                success=False,
                source="eastmoney",
                strategy=strategy,
                items=[],
                warnings=[],
                error_message="stock_code is required",
                error_type="parameter_error",
            )
        return self._fetch_report_scope(
            scope="stock",
            stock_code=normalized_stock_code,
            limit=limit,
            strategy=strategy,
            source_mode=source_mode,
        )

    def fetch_industry_reports(
        self,
        *,
        keyword: str = "医药",
        limit: int = 20,
        strategy: str = "auto",
        source_mode: str | None = None,
    ) -> dict:
        return self._fetch_report_scope(
            scope="industry",
            keyword=keyword,
            limit=limit,
            strategy=strategy,
            source_mode=source_mode,
        )

    def fetch_announcements(
        self,
        *,
        stock_code: str,
        begin_date: str | None = None,
        end_date: str | None = None,
        announcement_type: str = "全部",
        limit: int = 30,
        strategy: str = "auto",
        source_mode: str | None = None,
    ) -> dict:
        normalized_stock_code = _normalize_stock_code(stock_code)
        if not normalized_stock_code:
            return build_crawl_result(
                success=False,
                source="eastmoney",
                strategy=strategy,
                items=[],
                warnings=[],
                error_message="stock_code is required",
                error_type="parameter_error",
            )

        effective_mode = str(source_mode or self.config.source_mode or "auto").lower()
        if strategy == "fallback" or effective_mode == "fallback":
            return build_crawl_result(
                success=False,
                source="eastmoney",
                strategy="fallback",
                items=[],
                warnings=[],
                error_message="fallback mode is disabled for production report crawling",
                error_type="parameter_error",
            )

        warnings: list[str] = []
        last_error: CrawlRequestError | None = None
        if strategy in {"auto", "requests"}:
            try:
                items = self._fetch_announcements_json(
                    stock_code=normalized_stock_code,
                    begin_date=begin_date,
                    end_date=end_date,
                    announcement_type=announcement_type,
                    limit=limit,
                )
                if items:
                    return build_crawl_result(
                        success=True,
                        source="eastmoney",
                        strategy="requests/json",
                        items=items,
                        warnings=warnings,
                    )
                warnings.append("eastmoney announcement JSON returned no data")
            except CrawlRequestError as exc:
                last_error = exc
                warnings.append(f"requests/json failed: {exc.error_type}")

            try:
                items = self._fetch_announcements_html(stock_code=normalized_stock_code, limit=limit)
                if items:
                    return build_crawl_result(
                        success=True,
                        source="eastmoney",
                        strategy="requests/html",
                        items=items,
                        warnings=warnings,
                    )
                warnings.append("eastmoney announcement HTML returned no data")
            except CrawlRequestError as exc:
                last_error = exc
                warnings.append(f"requests/html failed: {exc.error_type}")

        if strategy in {"auto", "playwright"} and self.config.enable_playwright_fallback:
            try:
                items = self._fetch_announcements_html(stock_code=normalized_stock_code, limit=limit, strategy="playwright")
                if items:
                    return build_crawl_result(
                        success=True,
                        source="eastmoney",
                        strategy="playwright",
                        items=items,
                        warnings=warnings,
                    )
                warnings.append("playwright announcement fallback returned no data")
            except CrawlRequestError as exc:
                last_error = exc
                warnings.append(f"playwright failed: {exc.error_type}")

        return build_crawl_result(
            success=False,
            source="eastmoney",
            strategy=strategy,
            items=[],
            warnings=warnings,
            error_message=str(last_error.message if last_error else "eastmoney announcement fetch failed"),
            error_type=last_error.error_type if last_error else "no_data",
        )

    def _fetch_report_scope(
        self,
        *,
        scope: str,
        stock_code: str | None = None,
        keyword: str = "医药",
        limit: int,
        strategy: str,
        source_mode: str | None,
    ) -> dict:
        effective_mode = str(source_mode or self.config.source_mode or "auto").lower()
        if strategy == "fallback" or effective_mode == "fallback":
            return build_crawl_result(
                success=False,
                source="eastmoney",
                strategy="fallback",
                items=[],
                warnings=[],
                error_message="fallback mode is disabled for production report crawling",
                error_type="parameter_error",
            )

        warnings: list[str] = []
        last_error: CrawlRequestError | None = None
        if strategy in {"auto", "requests"}:
            try:
                items = self._fetch_reports_json(scope=scope, stock_code=stock_code, keyword=keyword, limit=limit)
                if items:
                    return build_crawl_result(
                        success=True,
                        source="eastmoney",
                        strategy="requests/json",
                        items=items,
                        warnings=warnings,
                    )
                warnings.append(f"eastmoney {scope} JSON returned no data")
            except CrawlRequestError as exc:
                last_error = exc
                warnings.append(f"requests/json failed: {exc.error_type}")

            try:
                items = self._fetch_reports_html(scope=scope, stock_code=stock_code, keyword=keyword, limit=limit)
                if items:
                    return build_crawl_result(
                        success=True,
                        source="eastmoney",
                        strategy="requests/html",
                        items=items,
                        warnings=warnings,
                    )
                warnings.append(f"eastmoney {scope} HTML returned no data")
            except CrawlRequestError as exc:
                last_error = exc
                warnings.append(f"requests/html failed: {exc.error_type}")

        if strategy in {"auto", "playwright"} and self.config.enable_playwright_fallback:
            try:
                items = self._fetch_reports_html(
                    scope=scope,
                    stock_code=stock_code,
                    keyword=keyword,
                    limit=limit,
                    strategy="playwright",
                )
                if items:
                    return build_crawl_result(
                        success=True,
                        source="eastmoney",
                        strategy="playwright",
                        items=items,
                        warnings=warnings,
                    )
                warnings.append(f"playwright {scope} fallback returned no data")
            except CrawlRequestError as exc:
                last_error = exc
                warnings.append(f"playwright failed: {exc.error_type}")

        return build_crawl_result(
            success=False,
            source="eastmoney",
            strategy=strategy,
            items=[],
            warnings=warnings,
            error_message=str(last_error.message if last_error else f"eastmoney {scope} fetch failed"),
            error_type=last_error.error_type if last_error else "no_data",
        )

    def _fetch_reports_json(self, *, scope: str, stock_code: str | None, keyword: str, limit: int) -> list[dict]:
        params = {
            "industryCode": "*",
            "pageSize": str(max(limit * 4, 20)),
            "industry": "*",
            "rating": "*",
            "ratingChange": "*",
            "beginTime": "2000-01-01",
            "endTime": f"{datetime.now().year + 1}-01-01",
            "pageNo": "1",
            "fields": "",
            "qType": "0",
            "orgCode": "",
            "rcode": "",
            "p": "1",
            "pageNum": "1",
            "pageNumber": "1",
        }
        if scope == "stock":
            params["code"] = stock_code
        else:
            params["code"] = "*"

        payload, _ = self.http.get_json("https://reportapi.eastmoney.com/report/list", params=params)
        data = (payload or {}).get("data") or []
        if not isinstance(data, list):
            raise CrawlRequestError("structure_changed", "eastmoney report payload missing list data", strategy="requests")

        items: list[dict] = []
        for raw in data:
            title = str(raw.get("title") or "").strip()
            if not title:
                continue
            item = {
                "title": title,
                "org": str(raw.get("orgSName") or raw.get("orgName") or "").strip() or None,
                "publish_date": _normalize_date(raw.get("publishDate")),
                "stock_code": _normalize_stock_code(raw.get("stockCode")),
                "stock_name": str(raw.get("stockName") or "").strip() or None,
                "industry": str(raw.get("indvInduName") or raw.get("industryName") or "").strip() or None,
                "rating": str(raw.get("emRatingName") or raw.get("ratingName") or "").strip() or None,
                "summary": str(raw.get("summary") or raw.get("title") or "").strip() or None,
                "source_site": "eastmoney",
                "report_type": "stock" if scope == "stock" else "industry",
                "source_url": self._build_report_source_url(raw, scope=scope, stock_code=stock_code),
                "pdf_url": self._build_report_pdf_url(raw),
            }
            if scope == "industry":
                matched = keyword in title or keyword in str(item.get("industry") or "") or keyword in str(item.get("summary") or "")
                if keyword and not matched:
                    continue
            items.append(item)
            if len(items) >= max(limit, 1):
                break
        return items

    def _fetch_reports_html(
        self,
        *,
        scope: str,
        stock_code: str | None,
        keyword: str,
        limit: int,
        strategy: str = "requests",
    ) -> list[dict]:
        url = "https://data.eastmoney.com/report/stock.jshtml"
        params = None
        if scope == "industry":
            url = "https://data.eastmoney.com/report/industry.jshtml"
        elif stock_code:
            params = {"code": stock_code}

        html, _ = self.http.get_text(url, params=params, strategy=strategy)
        if scope == "industry":
            inline_items = self._parse_industry_inline_data(html, keyword=keyword, limit=limit)
            if inline_items:
                return inline_items
        soup = BeautifulSoup(html, "lxml")
        rows = soup.select("table tbody tr") or soup.select("table.tab1 tr")
        if not rows:
            return []

        items: list[dict] = []
        for row in rows[: max(limit * 2, 10)]:
            cols = row.select("td")
            if len(cols) < 3:
                continue
            anchor = cols[0].find("a")
            title = anchor.get_text(strip=True) if anchor else cols[0].get_text(strip=True)
            if not title:
                continue
            item = {
                "title": title,
                "org": cols[1].get_text(strip=True) if len(cols) > 1 else None,
                "publish_date": _normalize_date(cols[2].get_text(strip=True) if len(cols) > 2 else None),
                "stock_code": stock_code,
                "stock_name": None,
                "industry": keyword if scope == "industry" else None,
                "rating": cols[3].get_text(strip=True) if len(cols) > 3 else None,
                "summary": title,
                "source_site": "eastmoney",
                "report_type": "stock" if scope == "stock" else "industry",
                "source_url": anchor.get("href") if anchor else url,
                "pdf_url": None,
            }
            if scope == "industry" and keyword and keyword not in title:
                continue
            items.append(item)
            if len(items) >= max(limit, 1):
                break
        return items

    def _parse_industry_inline_data(self, html: str, *, keyword: str, limit: int) -> list[dict]:
        marker = "var initdata= "
        start = html.find(marker)
        if start < 0:
            return []
        start += len(marker)
        raw_payload = self._extract_balanced_json_object(html[start:])
        if not raw_payload:
            return []
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            return []

        rows = payload.get("data") or []
        if not isinstance(rows, list):
            return []

        items: list[dict] = []
        for raw in rows:
            title = str(raw.get("title") or "").strip()
            industry_name = str(raw.get("industryName") or "").strip()
            summary = str(raw.get("title") or "").strip()
            if keyword and keyword not in title and keyword not in industry_name and keyword not in summary:
                continue
            info_code = str(raw.get("infoCode") or "").strip()
            items.append(
                {
                    "title": title,
                    "org": str(raw.get("orgSName") or raw.get("orgName") or "").strip() or None,
                    "publish_date": _normalize_date(raw.get("publishDate")),
                    "stock_code": None,
                    "stock_name": None,
                    "industry": industry_name or None,
                    "rating": str(raw.get("sRatingName") or raw.get("emRatingName") or "").strip() or None,
                    "summary": summary or None,
                    "source_site": "eastmoney",
                    "report_type": "industry",
                    "source_url": f"https://data.eastmoney.com/report/industry.jshtml#{info_code}" if info_code else "https://data.eastmoney.com/report/industry.jshtml",
                    "pdf_url": self._build_report_pdf_url(raw),
                }
            )
            if len(items) >= max(limit, 1):
                break
        return items

    def _extract_balanced_json_object(self, text: str) -> str:
        start = text.find("{")
        if start < 0:
            return ""
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(text)):
            char = text[index]
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start:index + 1]
        return ""

    def _fetch_announcements_json(
        self,
        *,
        stock_code: str,
        begin_date: str | None,
        end_date: str | None,
        announcement_type: str,
        limit: int,
    ) -> list[dict]:
        report_map = {
            "全部": "0",
            "财务报告": "1",
            "融资公告": "2",
            "风险提示": "3",
            "信息变更": "4",
            "重大事项": "5",
            "资产重组": "6",
            "持股变动": "7",
        }
        params = {
            "sr": "-1",
            "page_size": str(max(min(limit, 100), 1)),
            "page_index": "1",
            "ann_type": "A",
            "client_source": "web",
            "f_node": report_map.get(announcement_type, "0"),
            "s_node": "0",
            "stock_list": stock_code,
        }
        if begin_date:
            params["begin_time"] = begin_date
        if end_date:
            params["end_time"] = end_date

        payload, _ = self.http.get_json("https://np-anotice-stock.eastmoney.com/api/security/ann", params=params)
        root = (payload or {}).get("data") or {}
        rows = root.get("list") or []
        if not isinstance(rows, list):
            raise CrawlRequestError("structure_changed", "eastmoney announcement payload missing list", strategy="requests")

        items: list[dict] = []
        for raw in rows:
            code_entry = self._pick_announcement_code(raw)
            if not code_entry:
                continue
            normalized_stock_code = _normalize_stock_code(code_entry.get("stock_code") or stock_code)
            title = str(raw.get("title") or "").strip()
            publish_date = _normalize_date(raw.get("notice_date"))
            art_code = str(raw.get("art_code") or "").strip() or None
            source_url = _json_detail_url(normalized_stock_code, art_code)
            items.append(
                {
                    "stock_code": normalized_stock_code,
                    "title": title,
                    "publish_date": publish_date,
                    "exchange": _infer_exchange(normalized_stock_code),
                    "announcement_type": str((raw.get("columns") or [{}])[0].get("column_name") or raw.get("column_name") or "公告").strip() or "公告",
                    "source_url": source_url,
                    "source_type": "eastmoney_announcement_api",
                    "content": "\n".join(part for part in [title, publish_date, source_url] if part),
                    "file_hash": hashlib.md5(f"{normalized_stock_code}|{title}|{publish_date or ''}|{source_url or ''}".encode("utf-8")).hexdigest(),
                }
            )
        return items

    def _fetch_announcements_html(self, *, stock_code: str, limit: int, strategy: str = "requests") -> list[dict]:
        html, _ = self.http.get_text(
            "https://data.eastmoney.com/notices/stock/{}.html".format(stock_code),
            strategy=strategy,
        )
        soup = BeautifulSoup(html, "lxml")
        rows = soup.select("table tbody tr") or soup.select("li")
        items: list[dict] = []
        for row in rows[: max(limit * 2, 10)]:
            anchor = row.find("a")
            if anchor is None:
                continue
            title = anchor.get_text(strip=True)
            if not title:
                continue
            date_text = ""
            for cell in row.select("td"):
                cell_text = cell.get_text(strip=True)
                if _normalize_date(cell_text):
                    date_text = cell_text
                    break
            source_url = anchor.get("href") or ""
            items.append(
                {
                    "stock_code": stock_code,
                    "title": title,
                    "publish_date": _normalize_date(date_text),
                    "exchange": _infer_exchange(stock_code),
                    "announcement_type": "公告",
                    "source_url": source_url,
                    "source_type": "eastmoney_announcement_html",
                    "content": title,
                    "file_hash": hashlib.md5(f"{stock_code}|{title}|{date_text}|{source_url}".encode("utf-8")).hexdigest(),
                }
            )
            if len(items) >= max(limit, 1):
                break
        return items

    def _pick_announcement_code(self, raw: dict) -> dict | None:
        codes = raw.get("codes") or []
        if not isinstance(codes, list):
            return None
        if len(codes) == 1:
            return codes[0]
        for code in codes:
            if str(code.get("ann_type") or "").startswith("A"):
                return code
        return codes[0] if codes else None

    def _build_report_source_url(self, raw: dict, *, scope: str, stock_code: str | None) -> str | None:
        info_code = str(raw.get("infoCode") or "").strip()
        if info_code:
            if scope == "stock":
                return f"https://data.eastmoney.com/report/info/{info_code}.html"
            return f"https://data.eastmoney.com/report/industry.jshtml"
        if scope == "stock" and stock_code:
            return f"https://data.eastmoney.com/report/stock.jshtml?code={stock_code}"
        return "https://data.eastmoney.com/report/industry.jshtml"

    def _build_report_pdf_url(self, raw: dict) -> str | None:
        info_code = str(raw.get("infoCode") or "").strip()
        if not info_code:
            return None
        return f"https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf"

    def _fallback_reports(self, *, scope: str, warning: str | None = None) -> dict:
        payload = load_sample_json("research_report_sample.json")
        items = [
            item
            for item in (payload.get("items") or [])
            if str(item.get("report_type") or "").strip() == scope
        ]
        return build_crawl_result(
            success=bool(items),
            source="local-sample",
            strategy="fallback",
            items=items,
            warnings=[warning] if warning else [],
            error_message=None if items else "research report sample is empty",
            error_type=None if items else "no_data",
        )

    def _fallback_announcements(self, *, stock_code: str, warning: str | None = None) -> dict:
        payload = load_sample_json("announcement_sample.json")
        items = [
            item
            for item in (payload.get("items") or [])
            if _normalize_stock_code(item.get("stock_code")) == stock_code
        ]
        if not items:
            items = payload.get("items") or []
        return build_crawl_result(
            success=bool(items),
            source="local-sample",
            strategy="fallback",
            items=items,
            warnings=[warning] if warning else [],
            error_message=None if items else "announcement sample is empty",
            error_type=None if items else "no_data",
        )


__all__ = ["EastmoneyClient"]