from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from time import time
from urllib.parse import urlencode
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from crawler.clients.http_client import (
    CrawlerRuntimeConfig,
    CrawlRequestError,
    SiteHttpClient,
    build_crawl_result,
    load_sample_json,
)


DEFAULT_ENDPOINT = "https://data.stats.gov.cn/easyquery.htm"
DEFAULT_DBCODE = "hgyd"
RELEASE_LISTING_URL = "https://www.stats.gov.cn/sj/zxfb/"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    "Referer": "https://data.stats.gov.cn/easyquery.htm?cn=A01",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}
_QUARTER_CODE_MAP = {"A": "Q1", "B": "Q2", "C": "Q3", "D": "Q4"}
_QUARTER_TEXT_MAP = {
    "1季度": "Q1",
    "2季度": "Q2",
    "3季度": "Q3",
    "4季度": "Q4",
    "一季度": "Q1",
    "二季度": "Q2",
    "三季度": "Q3",
    "四季度": "Q4",
}

DEFAULT_INDICATOR_SPECS = [
    {
        "indicator_name": "居民消费价格指数(上年同月=100)",
        "indicator_code": "A01010101",
        "unit": "%",
    },
    {
        "indicator_name": "医疗保健类居民消费价格指数(上年同月=100)",
        "indicator_code": "A01010801",
        "unit": "%",
    },
    {
        "indicator_name": "工业生产者出厂价格指数(上年同月=100)",
        "indicator_code": "A01020101",
        "unit": "%",
    },
]


class StatsGovFetchError(RuntimeError):
    pass


def _compact_json(value: list[dict] | dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _build_query_params(
    indicator_code: str,
    *,
    dbcode: str,
    rowcode: str,
    colcode: str,
    wds: list[dict] | None,
    dfwds: list[dict] | None,
    page: int,
    pagesize: int,
) -> dict[str, str | int]:
    query_wds = list(wds or [])
    query_dfwds = list(dfwds or [])

    if not any(str(item.get("wdcode") or "").strip() == "zb" for item in query_wds + query_dfwds):
        query_dfwds.insert(0, {"wdcode": "zb", "valuecode": indicator_code})

    return {
        "m": "QueryData",
        "dbcode": dbcode,
        "rowcode": rowcode,
        "colcode": colcode,
        "wds": _compact_json(query_wds),
        "dfwds": _compact_json(query_dfwds),
        "page": page,
        "pagesize": pagesize,
        "sorttype": 0,
        "k1": int(time() * 1000),
    }


def _build_query_url(endpoint: str, params: dict[str, str | int]) -> str:
    return f"{endpoint}?{urlencode(params)}"


def _build_series_result(
    payload: dict,
    *,
    indicator_code: str,
    indicator_name: str | None,
    unit: str | None,
    dbcode: str,
    query_url: str,
) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("stats.gov response is not a JSON object")

    return {
        "indicator_code": indicator_code,
        "indicator_name": str(indicator_name or "").strip() or None,
        "unit": str(unit or "").strip() or None,
        "dbcode": dbcode,
        "query_url": query_url,
        "response": payload,
    }


def _browser_fetch_json(query_url: str, *, timeout: int, referer_url: str) -> dict:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise StatsGovFetchError(
            "browser mode requires optional dependency 'playwright'. "
            "Install it with 'pip install playwright' and then run 'playwright install chromium'."
        ) from exc

    timeout_ms = max(timeout, 1) * 1000
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(extra_http_headers=DEFAULT_HEADERS)
            page = context.new_page()
            page.goto(referer_url, wait_until="domcontentloaded", timeout=timeout_ms)
            response_payload = page.evaluate(
                """
                async ({ queryUrl }) => {
                    const response = await fetch(queryUrl, {
                        method: 'GET',
                        credentials: 'include',
                        headers: {
                            'Accept': 'application/json, text/javascript, */*; q=0.01',
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });
                    const text = await response.text();
                    return {
                        ok: response.ok,
                        status: response.status,
                        statusText: response.statusText,
                        text,
                    };
                }
                """,
                {"queryUrl": query_url},
            )
            browser.close()
    except PlaywrightTimeoutError as exc:
        raise StatsGovFetchError(f"browser mode timed out after {timeout}s while opening stats.gov.cn") from exc
    except PlaywrightError as exc:
        raise StatsGovFetchError(f"browser mode failed: {exc}") from exc
    except Exception as exc:
        raise StatsGovFetchError(f"browser mode failed unexpectedly: {exc}") from exc

    if not isinstance(response_payload, dict):
        raise StatsGovFetchError("browser mode returned an unexpected response payload")
    if not response_payload.get("ok"):
        status = response_payload.get("status")
        status_text = response_payload.get("statusText")
        body = str(response_payload.get("text") or "").strip()
        detail = body[:200] if body else "empty response body"
        raise StatsGovFetchError(f"browser mode got HTTP {status} {status_text}: {detail}")

    try:
        return json.loads(str(response_payload.get("text") or ""))
    except json.JSONDecodeError as exc:
        raise StatsGovFetchError("browser mode returned a non-JSON response from stats.gov.cn") from exc


def _build_dimension_lookup(wdnodes: list[dict]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for wd in wdnodes:
        wdcode = str(wd.get("wdcode") or "").strip()
        if not wdcode:
            continue
        nodes = wd.get("nodes") or []
        lookup[wdcode] = {
            str(node.get("code") or "").strip(): str(node.get("cname") or node.get("name") or "").strip()
            for node in nodes
            if str(node.get("code") or "").strip()
        }
    return lookup


def _extract_wd_value(node: dict, wdcode: str) -> str:
    for wd in node.get("wds") or []:
        if str(wd.get("wdcode") or "").strip() == wdcode:
            return str(wd.get("valuecode") or "").strip()
    return ""


def _extract_numeric_value(node: dict) -> str | None:
    data = node.get("data")
    raw_value = data if not isinstance(data, dict) else data.get("strdata")
    if raw_value in (None, "", "--") and isinstance(data, dict):
        raw_value = data.get("data")
    if raw_value in (None, "", "--"):
        return None

    text = str(raw_value).replace(",", "").strip()
    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError):
        return None

    normalized = format(value, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def normalize_period(value) -> str | None:
    if value is None:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    upper_raw = raw.upper()
    year_match = re.search(r"(\d{4})", raw)
    if year_match:
        year = year_match.group(1)
        for token, quarter in _QUARTER_TEXT_MAP.items():
            if token in raw:
                return f"{year}-{quarter}"

        code_match = re.fullmatch(r"(\d{4})([ABCD])", upper_raw)
        if code_match:
            return f"{code_match.group(1)}-{_QUARTER_CODE_MAP[code_match.group(2)]}"

        quarter_match = re.fullmatch(r"(\d{4})[-_/ ]?Q([1-4])", upper_raw)
        if quarter_match:
            return f"{quarter_match.group(1)}-Q{quarter_match.group(2)}"

    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) == 4:
        return digits
    if len(digits) == 6:
        month = int(digits[4:6])
        if 1 <= month <= 12:
            return f"{digits[:4]}-{month:02d}"
    if len(digits) >= 8:
        year = digits[:4]
        month = int(digits[4:6])
        day = int(digits[6:8])
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year}-{month:02d}-{day:02d}"

    dash_month = re.fullmatch(r"(\d{4})-(\d{1,2})", raw.replace("/", "-").replace(".", "-"))
    if dash_month:
        return f"{dash_month.group(1)}-{int(dash_month.group(2)):02d}"

    return raw


def fetch_indicator_series(
    indicator_code: str,
    *,
    indicator_name: str | None = None,
    unit: str | None = None,
    dbcode: str = DEFAULT_DBCODE,
    endpoint: str = DEFAULT_ENDPOINT,
    rowcode: str = "sj",
    colcode: str = "zb",
    wds: list[dict] | None = None,
    dfwds: list[dict] | None = None,
    page: int = 1,
    pagesize: int = 120,
    timeout: int = 30,
) -> dict:
    params = _build_query_params(
        indicator_code,
        dbcode=dbcode,
        rowcode=rowcode,
        colcode=colcode,
        wds=wds,
        dfwds=dfwds,
        page=page,
        pagesize=pagesize,
    )

    response = requests.get(
        endpoint,
        params=params,
        headers=DEFAULT_HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    return _build_series_result(
        payload,
        indicator_code=indicator_code,
        indicator_name=indicator_name,
        unit=unit,
        dbcode=dbcode,
        query_url=_build_query_url(endpoint, params),
    )


def fetch_indicator_series_with_browser(
    indicator_code: str,
    *,
    indicator_name: str | None = None,
    unit: str | None = None,
    dbcode: str = DEFAULT_DBCODE,
    endpoint: str = DEFAULT_ENDPOINT,
    rowcode: str = "sj",
    colcode: str = "zb",
    wds: list[dict] | None = None,
    dfwds: list[dict] | None = None,
    page: int = 1,
    pagesize: int = 120,
    timeout: int = 30,
) -> dict:
    params = _build_query_params(
        indicator_code,
        dbcode=dbcode,
        rowcode=rowcode,
        colcode=colcode,
        wds=wds,
        dfwds=dfwds,
        page=page,
        pagesize=pagesize,
    )
    query_url = _build_query_url(endpoint, params)
    payload = _browser_fetch_json(query_url, timeout=timeout, referer_url=DEFAULT_HEADERS["Referer"])
    return _build_series_result(
        payload,
        indicator_code=indicator_code,
        indicator_name=indicator_name,
        unit=unit,
        dbcode=dbcode,
        query_url=query_url,
    )


def fetch_indicator_series_live(
    indicator_code: str,
    *,
    indicator_name: str | None = None,
    unit: str | None = None,
    dbcode: str = DEFAULT_DBCODE,
    endpoint: str = DEFAULT_ENDPOINT,
    rowcode: str = "sj",
    colcode: str = "zb",
    wds: list[dict] | None = None,
    dfwds: list[dict] | None = None,
    page: int = 1,
    pagesize: int = 120,
    timeout: int = 30,
    allow_requests_fallback: bool = True,
) -> dict:
    browser_error: Exception | None = None
    try:
        return fetch_indicator_series_with_browser(
            indicator_code,
            indicator_name=indicator_name,
            unit=unit,
            dbcode=dbcode,
            endpoint=endpoint,
            rowcode=rowcode,
            colcode=colcode,
            wds=wds,
            dfwds=dfwds,
            page=page,
            pagesize=pagesize,
            timeout=timeout,
        )
    except Exception as exc:
        browser_error = exc

    if allow_requests_fallback:
        try:
            return fetch_indicator_series(
                indicator_code,
                indicator_name=indicator_name,
                unit=unit,
                dbcode=dbcode,
                endpoint=endpoint,
                rowcode=rowcode,
                colcode=colcode,
                wds=wds,
                dfwds=dfwds,
                page=page,
                pagesize=pagesize,
                timeout=timeout,
            )
        except Exception as request_exc:
            raise StatsGovFetchError(
                "stats.gov live fetch failed in both browser mode and requests mode. "
                f"browser_error={browser_error}; requests_error={request_exc}"
            ) from request_exc

    raise StatsGovFetchError(f"stats.gov live fetch failed in browser mode: {browser_error}")


def build_macro_items(series_result: dict, *, source_type: str = "stats_gov") -> list[dict]:
    payload = series_result.get("response") or {}
    returndata = payload.get("returndata") or {}
    wdnodes = returndata.get("wdnodes") or []
    datanodes = returndata.get("datanodes") or []
    lookup = _build_dimension_lookup(wdnodes)
    indicator_lookup = lookup.get("zb") or {}
    period_lookup = lookup.get("sj") or {}
    default_indicator_code = str(series_result.get("indicator_code") or "").strip()
    default_indicator_name = (
        str(series_result.get("indicator_name") or "").strip()
        or indicator_lookup.get(default_indicator_code)
        or default_indicator_code
    )
    default_unit = str(series_result.get("unit") or "").strip() or None
    source_url = str(series_result.get("query_url") or "").strip() or None

    items: list[dict] = []
    for node in datanodes:
        indicator_code = _extract_wd_value(node, "zb") or default_indicator_code
        indicator_name = indicator_lookup.get(indicator_code) or default_indicator_name
        period_code = _extract_wd_value(node, "sj")
        period_label = period_lookup.get(period_code) or period_code
        period = normalize_period(period_label)
        value = _extract_numeric_value(node)
        if not indicator_name or not period or value is None:
            continue

        items.append(
            {
                "indicator_name": indicator_name[:128],
                "period": period[:32],
                "value": value,
                "unit": default_unit,
                "source_type": source_type,
                "source_url": source_url,
            }
        )

    items.sort(key=lambda item: item["period"], reverse=True)
    return items


class StatsGovClient:
    def __init__(self, *, config: CrawlerRuntimeConfig | None = None) -> None:
        self.config = config or CrawlerRuntimeConfig.from_settings()
        self.http = SiteHttpClient("stats_gov", config=self.config)

    def fetch_series_bundle(
        self,
        indicators: list[dict] | None = None,
        *,
        dbcode: str = DEFAULT_DBCODE,
        limit_per_indicator: int = 12,
        strategy: str = "auto",
        source_mode: str | None = None,
    ) -> dict:
        indicator_specs = indicators or list(DEFAULT_INDICATOR_SPECS)
        effective_mode = str(source_mode or self.config.source_mode or "auto").lower()
        if strategy == "fallback" or effective_mode == "fallback":
            return build_crawl_result(
                success=False,
                source="stats_gov",
                strategy="fallback",
                data={"series_results": []},
                warnings=[],
                error_message="fallback mode is disabled for production macro crawling",
                error_type="parameter_error",
            )

        warnings: list[str] = []
        request_strategy = "playwright" if strategy == "playwright" else "requests"
        try:
            series_results = self._fetch_release_series(
                indicator_specs,
                limit_per_indicator=max(limit_per_indicator, 1),
                strategy=request_strategy,
            )
        except CrawlRequestError as exc:
            warnings.append(f"stats.gov release fetch failed: {exc.error_type}")
            series_results = []

        if series_results:
            expected_names = {
                str(item.get("indicator_name") or "").strip()
                for item in indicator_specs
                if str(item.get("indicator_name") or "").strip()
            }
            observed_names = {
                str(item.get("indicator_name") or "").strip()
                for item in series_results
                if str(item.get("indicator_name") or "").strip()
            }
            missing = sorted(name for name in expected_names if name and name not in observed_names)
            if missing:
                warnings.append(f"missing stats.gov release series for: {', '.join(missing)}")
            return build_crawl_result(
                success=not missing,
                source="stats_gov",
                strategy="playwright" if request_strategy == "playwright" else "requests/html",
                data={"series_results": series_results},
                warnings=warnings,
                error_message=None if not missing else f"missing macro indicators: {', '.join(missing)}",
                error_type=None if not missing else "no_data",
            )

        return build_crawl_result(
            success=False,
            source="stats_gov",
            strategy=strategy,
            data={"series_results": []},
            warnings=warnings,
            error_message="stats.gov series fetch failed",
            error_type="blocked" if any("blocked" in item for item in warnings) else "no_data",
        )

    def _fetch_release_series(self, indicators: list[dict], *, limit_per_indicator: int, strategy: str) -> list[dict]:
        topic_links: dict[str, list[tuple[str, str]]] = {}
        results: list[dict] = []
        for indicator in indicators:
            topic = self._indicator_topic(indicator)
            if topic not in topic_links:
                topic_links[topic] = self._collect_release_links(topic, needed=max(limit_per_indicator, 3), strategy=strategy)
            article_links = topic_links.get(topic) or []
            results.extend(self._extract_series_from_articles(indicator, article_links[:limit_per_indicator], strategy=strategy))
        deduped: dict[tuple[str, str], dict] = {}
        for item in results:
            key = (str(item.get("indicator_name") or "").strip(), str(item.get("period") or "").strip())
            if key[0] and key[1]:
                deduped[key] = item
        return sorted(deduped.values(), key=lambda item: (item["indicator_name"], item["period"]), reverse=True)

    def _collect_release_links(self, topic: str, *, needed: int, strategy: str) -> list[tuple[str, str]]:
        links: list[tuple[str, str]] = []
        seen: set[str] = set()
        for page_index in range(6):
            page_url = RELEASE_LISTING_URL if page_index == 0 else urljoin(RELEASE_LISTING_URL, f"index_{page_index}.html")
            html, _ = self.http.get_text(
                page_url,
                strategy=strategy,
                headers={
                    "Referer": RELEASE_LISTING_URL,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            html = self._normalize_html_text(html)
            soup = BeautifulSoup(html, "lxml")
            for anchor in soup.select("a[href]"):
                href = str(anchor.get("href") or "").strip()
                title = " ".join(anchor.stripped_strings)
                if not href or not title:
                    continue
                if not re.search(r"(?:^|/)(?:\d{6}/t\d+_\d+\.html)$", href):
                    continue
                if not self._title_matches_topic(title, topic):
                    continue
                url = urljoin(RELEASE_LISTING_URL, href)
                if url in seen:
                    continue
                seen.add(url)
                links.append((title, url))
                if len(links) >= needed:
                    return links
        return links

    def _extract_series_from_articles(self, indicator: dict, article_links: list[tuple[str, str]], *, strategy: str) -> list[dict]:
        indicator_name = str(indicator.get("indicator_name") or "").strip()
        unit = str(indicator.get("unit") or "%").strip() or "%"
        items: list[dict] = []
        for title, url in article_links:
            html, _ = self.http.get_text(
                url,
                strategy=strategy,
                headers={
                    "Referer": RELEASE_LISTING_URL,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            html = self._normalize_html_text(html)
            article_title, publish_date, article_text = self._parse_release_article(html, fallback_title=title)
            value = self._extract_release_value(indicator_name, article_text)
            period = self._extract_release_period(article_title, publish_date)
            if value is None or not period:
                continue
            items.append(
                {
                    "indicator_name": indicator_name,
                    "period": period,
                    "value": value,
                    "unit": unit,
                    "source_type": "stats_gov_release",
                    "source_url": url,
                }
            )
        return items

    def _indicator_topic(self, indicator: dict) -> str:
        indicator_name = str(indicator.get("indicator_name") or "").strip()
        if "采购经理指数" in indicator_name:
            return "pmi"
        if "工业生产者出厂价格" in indicator_name:
            return "ppi"
        return "cpi"

    def _title_matches_topic(self, title: str, topic: str) -> bool:
        normalized = str(title or "").strip()
        if topic == "cpi":
            return "居民消费价格" in normalized
        if topic == "ppi":
            return "工业生产者出厂价格" in normalized
        return "采购经理指数运行情况" in normalized

    def _parse_release_article(self, html: str, *, fallback_title: str) -> tuple[str, str | None, str]:
        soup = BeautifulSoup(html, "lxml")
        title = " ".join((soup.select_one("h1") or soup.select_one("title") or soup).stripped_strings)
        title = title.strip() or fallback_title
        text = "\n".join(part.strip() for part in soup.stripped_strings if part and part.strip())
        publish_match = re.search(r"(20\d{2})/(\d{2})/(\d{2})", text)
        publish_date = None
        if publish_match:
            publish_date = f"{publish_match.group(1)}-{publish_match.group(2)}-{publish_match.group(3)}"
        return title, publish_date, text

    def _extract_release_period(self, title: str, publish_date: str | None) -> str | None:
        title_match = re.search(r"(20\d{2})年(\d{1,2})月", title)
        if title_match:
            return f"{title_match.group(1)}-{int(title_match.group(2)):02d}"
        return normalize_period(publish_date)

    def _extract_release_value(self, indicator_name: str, article_text: str) -> str | None:
        flat_text = re.sub(r"\s+", " ", article_text).strip()
        if "医疗保健" in indicator_name:
            table_match = re.search(r"七、医疗保健\s*([-0-9.]+)\s*([-0-9.]+)\s*([-0-9.]+)", flat_text)
            if table_match:
                return table_match.group(2)
            return self._extract_signed_percent(flat_text, r"医疗保健[^。；]*?(上涨|下降)\s*([0-9]+(?:\.[0-9]+)?)%")
        if "居民消费价格" in indicator_name:
            return self._extract_signed_percent(flat_text, r"全国居民消费价格同比\s*(上涨|下降)\s*([0-9]+(?:\.[0-9]+)?)%")
        if "工业生产者出厂价格" in indicator_name:
            return self._extract_signed_percent(flat_text, r"全国工业生产者出厂价格同比(?:由上月(?:上涨|下降)\s*[0-9]+(?:\.[0-9]+)?%\s*转为)?\s*(上涨|下降)\s*([0-9]+(?:\.[0-9]+)?)%")
        if "采购经理指数" in indicator_name:
            match = re.search(r"制造业采购经理指数（PMI）为\s*([0-9]+(?:\.[0-9]+)?)%", flat_text)
            return match.group(1) if match else None
        return None

    def _extract_signed_percent(self, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, re.S)
        if not match:
            return None
        direction = str(match.group(1) or "").strip()
        value = str(match.group(2) or "").strip()
        if not value:
            return None
        return f"-{value}" if direction == "下降" else value

    def _normalize_html_text(self, text: str) -> str:
        if not text:
            return text
        if any(token in text for token in ("居民消费价格", "工业生产者出厂价格", "采购经理指数")):
            return text
        try:
            repaired = text.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
        except UnicodeError:
            return text
        return repaired or text

    def _fetch_indicator_json(self, indicator: dict, *, dbcode: str, limit_per_indicator: int) -> dict:
        params = _build_query_params(
            indicator["indicator_code"],
            dbcode=dbcode,
            rowcode="sj",
            colcode="zb",
            wds=None,
            dfwds=None,
            page=1,
            pagesize=max(limit_per_indicator, 12),
        )
        payload, _ = self.http.get_json(DEFAULT_ENDPOINT, params=params)
        return _build_series_result(
            payload,
            indicator_code=indicator["indicator_code"],
            indicator_name=indicator.get("indicator_name"),
            unit=indicator.get("unit"),
            dbcode=dbcode,
            query_url=_build_query_url(DEFAULT_ENDPOINT, params),
        )

    def _fetch_html_probe(self) -> None:
        html, _ = self.http.get_text(DEFAULT_HEADERS["Referer"], strategy="requests")
        if "403 Forbidden" in html or "UrlACL" in html:
            raise CrawlRequestError("blocked", "stats.gov HTML landing page is blocked", strategy="requests")
        raise CrawlRequestError("structure_changed", "stats.gov HTML page does not embed the requested series payload", strategy="requests")

    def _fallback_bundle(self, *, warning: str | None = None) -> dict:
        return build_crawl_result(
            success=False,
            source="stats_gov",
            strategy="fallback",
            data={"series_results": []},
            warnings=[warning] if warning else [],
            error_message="macro fallback is disabled",
            error_type="parameter_error",
        )


__all__ = [
    "DEFAULT_INDICATOR_SPECS",
    "DEFAULT_DBCODE",
    "DEFAULT_ENDPOINT",
    "StatsGovClient",
    "StatsGovFetchError",
    "build_macro_items",
    "fetch_indicator_series",
    "fetch_indicator_series_live",
    "fetch_indicator_series_with_browser",
    "normalize_period",
]