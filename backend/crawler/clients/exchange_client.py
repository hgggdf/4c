from __future__ import annotations

from datetime import datetime
import hashlib
import json

from .http_client import CrawlerRuntimeConfig, CrawlRequestError, SiteHttpClient, build_crawl_result, strip_jsonp


def _normalize_stock_code(value: str | None) -> str | None:
    digits = "".join(ch for ch in str(value or "").strip() if ch.isdigit())
    if len(digits) >= 6:
        return digits[-6:]
    return digits or None


def _normalize_date(value) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    text = text.replace("/", "-").replace(".", "-")
    if len(text) >= 10:
        return text[:10]
    return None


def _infer_exchange(stock_code: str | None) -> str:
    code = str(stock_code or "")
    if code.startswith(("60", "68", "90")):
        return "SSE"
    if code.startswith(("00", "20", "30")):
        return "SZSE"
    if code.startswith(("43", "83", "87", "92")):
        return "BSE"
    return "SSE"


class ExchangeAnnouncementClient:
    def __init__(self, *, config: CrawlerRuntimeConfig | None = None) -> None:
        self.config = config or CrawlerRuntimeConfig.from_settings()
        self.sse_http = SiteHttpClient("sse", config=self.config)
        self.szse_http = SiteHttpClient("szse", config=self.config)
        self.bse_http = SiteHttpClient("bse", config=self.config)

    def fetch_announcements(
        self,
        stock_code: str,
        *,
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
                source="exchange",
                strategy=strategy,
                items=[],
                warnings=[],
                error_message="stock_code is required",
                error_type="parameter_error",
            )

        exchange = _infer_exchange(normalized_stock_code)
        effective_mode = str(source_mode or self.config.source_mode or "auto").lower()
        if strategy == "fallback" or effective_mode == "fallback":
            return build_crawl_result(
                success=False,
                source=exchange.lower(),
                strategy="fallback",
                items=[],
                warnings=[],
                error_message="fallback mode is disabled for production announcement crawling",
                error_type="parameter_error",
            )

        warnings: list[str] = []
        if strategy in {"auto", "requests"}:
            if exchange == "SSE":
                try:
                    items = self._fetch_sse_json(
                        stock_code=normalized_stock_code,
                        begin_date=begin_date,
                        end_date=end_date,
                        limit=limit,
                    )
                    if items:
                        return build_crawl_result(
                            success=True,
                            source="sse",
                            strategy="requests/json",
                            items=items,
                            warnings=warnings,
                        )
                    warnings.append("sse requests/json returned no data")
                except CrawlRequestError as exc:
                    warnings.append(f"sse requests/json failed: {exc.error_type}")
            elif exchange == "SZSE":
                try:
                    items = self._fetch_szse_json(
                        stock_code=normalized_stock_code,
                        begin_date=begin_date,
                        end_date=end_date,
                        limit=limit,
                    )
                    if items:
                        return build_crawl_result(
                            success=True,
                            source="szse",
                            strategy="requests/json",
                            items=items,
                            warnings=warnings,
                        )
                    warnings.append("szse requests/json returned no data")
                except CrawlRequestError as exc:
                    warnings.append(f"szse requests/json failed: {exc.error_type}")
            else:
                try:
                    items = self._fetch_bse_json(
                        stock_code=normalized_stock_code,
                        begin_date=begin_date,
                        end_date=end_date,
                        limit=limit,
                    )
                    if items:
                        return build_crawl_result(
                            success=True,
                            source="bse",
                            strategy="requests/jsonp",
                            items=items,
                            warnings=warnings,
                        )
                    warnings.append("bse requests/jsonp returned no data")
                except CrawlRequestError as exc:
                    warnings.append(f"bse requests/jsonp failed: {exc.error_type}")

        return build_crawl_result(
            success=False,
            source=exchange.lower(),
            strategy=strategy,
            items=[],
            warnings=warnings,
            error_message="announcement fetch failed",
            error_type="no_data",
        )

    def _fetch_sse_json(
        self,
        *,
        stock_code: str,
        begin_date: str | None,
        end_date: str | None,
        limit: int,
    ) -> list[dict]:
        params = {
            "jsonCallBack": "jsonpCallbackSSE",
            "isPagination": "true",
            "pageHelp.pageSize": max(min(limit, 50), 1),
            "pageHelp.pageNo": 1,
            "pageHelp.beginPage": 1,
            "pageHelp.cacheSize": 1,
            "START_DATE": begin_date or "",
            "END_DATE": end_date or "",
            "SECURITY_CODE": stock_code,
            "TITLE": "",
            "BULLETIN_TYPE": "",
            "stockType": "",
        }
        payload, _ = self.sse_http.get_json(
            "https://query.sse.com.cn/security/stock/queryCompanyBulletinNew.do",
            params=params,
            jsonp=True,
        )
        page_help = (payload or {}).get("pageHelp") or {}
        rows = page_help.get("data") or []
        items: list[dict] = []
        for row in rows:
            raw = row[0] if isinstance(row, list) and row else row
            if not isinstance(raw, dict):
                continue
            title = str(raw.get("TITLE") or "").strip()
            publish_date = _normalize_date(raw.get("SSEDATE"))
            source_url = str(raw.get("URL") or "").strip()
            if source_url.startswith("/"):
                source_url = f"https://www.sse.com.cn{source_url}"
            items.append(
                {
                    "stock_code": stock_code,
                    "title": title,
                    "publish_date": publish_date,
                    "exchange": "SSE",
                    "announcement_type": str(raw.get("BULLETIN_TYPE_DESC") or "公告").strip() or "公告",
                    "source_url": source_url or None,
                    "source_type": "sse_announcement_api",
                    "content": "\n".join(part for part in [title, publish_date, source_url] if part),
                    "file_hash": hashlib.md5(f"{stock_code}|{title}|{publish_date or ''}|{source_url or ''}".encode("utf-8")).hexdigest(),
                }
            )
        return items

    def _fetch_szse_json(
        self,
        *,
        stock_code: str,
        begin_date: str | None,
        end_date: str | None,
        limit: int,
    ) -> list[dict]:
        payload, _ = self.szse_http.post_json(
            "https://www.szse.cn/api/disc/announcement/annList",
            params={"random": f"0.{datetime.now().microsecond:06d}"},
            json_body={
                "seDate": [begin_date or "2025-01-01", end_date or datetime.now().date().isoformat()],
                "stock": [stock_code],
                "channelCode": ["listedNotice_disc"],
                "pageSize": max(min(limit, 50), 1),
                "pageNum": 1,
            },
            headers={"Content-Type": "application/json"},
            strategy="requests",
        )
        rows = (payload or {}).get("data") or []
        if not isinstance(rows, list):
            raise CrawlRequestError("structure_changed", "szse payload missing data list", strategy="requests")

        items: list[dict] = []
        for raw in rows:
            title = str(raw.get("title") or "").strip()
            publish_date = _normalize_date(raw.get("publishTime"))
            attachment_path = str(raw.get("attachPath") or "").strip()
            if attachment_path.startswith("/"):
                attachment_path = f"https://disc.static.szse.cn{attachment_path}"
            items.append(
                {
                    "stock_code": _normalize_stock_code((raw.get("secCode") or [stock_code])[0] if isinstance(raw.get("secCode"), list) else raw.get("secCode") or stock_code),
                    "title": title,
                    "publish_date": publish_date,
                    "exchange": "SZSE",
                    "announcement_type": "公告",
                    "source_url": attachment_path or None,
                    "source_type": "szse_announcement_api",
                    "content": "\n".join(part for part in [title, publish_date, attachment_path] if part),
                    "file_hash": hashlib.md5(f"{stock_code}|{title}|{publish_date or ''}|{attachment_path or ''}".encode("utf-8")).hexdigest(),
                }
            )
        return items

    def _fetch_bse_json(
        self,
        *,
        stock_code: str,
        begin_date: str | None,
        end_date: str | None,
        limit: int,
    ) -> list[dict]:
        body = [
            ("disclosureType[]", "5"),
            ("disclosureSubtype[]", ""),
            ("page", ""),
            ("companyCd", stock_code),
            ("isNewThree", "1"),
            ("startTime", begin_date or "2025-01-01"),
            ("endTime", end_date or datetime.now().date().isoformat()),
            ("keyword", ""),
            ("xxfcbj[]", "2"),
        ]
        for field in [
            "companyCd",
            "companyName",
            "disclosureTitle",
            "disclosurePostTitle",
            "destFilePath",
            "publishDate",
            "xxfcbj",
            "destFilePath",
            "fileExt",
            "xxzrlx",
        ]:
            body.append(("needFields[]", field))
        body.extend([
            ("sortfield", "xxssdq"),
            ("sorttype", "asc"),
        ])
        text, _ = self.bse_http.post_text(
            "https://www.bse.cn/disclosureInfoController/companyAnnouncement.do",
            params={"callback": "callbackBSE"},
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
            strategy="requests",
        )
        try:
            payload = json.loads(strip_jsonp(text))
        except json.JSONDecodeError as exc:
            raise CrawlRequestError("interface_invalid", "bse payload is not valid JSONP", strategy="requests") from exc
        if not isinstance(payload, list) or not payload:
            raise CrawlRequestError("structure_changed", "bse payload missing list root", strategy="requests")
        rows = (((payload[0] or {}).get("listInfo") or {}).get("content")) or []
        if not isinstance(rows, list):
            raise CrawlRequestError("structure_changed", "bse payload missing content list", strategy="requests")

        items: list[dict] = []
        for raw in rows[: max(limit, 1)]:
            title = str(raw.get("disclosureTitle") or "").strip()
            publish_date = _normalize_date(raw.get("publishDate"))
            source_url = str(raw.get("destFilePath") or "").strip()
            if source_url.startswith("/"):
                source_url = f"https://www.bse.cn{source_url}"
            normalized_code = _normalize_stock_code(raw.get("companyCd") or stock_code) or stock_code
            items.append(
                {
                    "stock_code": normalized_code,
                    "title": title,
                    "publish_date": publish_date,
                    "exchange": "BSE",
                    "announcement_type": "公告",
                    "source_url": source_url or None,
                    "source_type": "bse_announcement_api",
                    "content": "\n".join(part for part in [title, publish_date, source_url] if part),
                    "file_hash": hashlib.md5(f"{normalized_code}|{title}|{publish_date or ''}|{source_url or ''}".encode("utf-8")).hexdigest(),
                }
            )
        return items


__all__ = ["ExchangeAnnouncementClient"]