from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from time import time
from urllib.parse import urlencode

import requests


DEFAULT_ENDPOINT = "https://data.stats.gov.cn/easyquery.htm"
DEFAULT_DBCODE = "hgyd"
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


__all__ = [
    "DEFAULT_DBCODE",
    "DEFAULT_ENDPOINT",
    "StatsGovFetchError",
    "build_macro_items",
    "fetch_indicator_series",
    "fetch_indicator_series_live",
    "fetch_indicator_series_with_browser",
    "normalize_period",
]