from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException

from config import get_settings

try:
    from curl_cffi import requests as curl_requests
except Exception:
    curl_requests = None


USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/133.0.0.0 Safari/537.36"
    ),
]

SITE_HEADERS = {
    "eastmoney": {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://data.eastmoney.com/",
        "Origin": "https://data.eastmoney.com",
    },
    "sse": {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.sse.com.cn/disclosure/listedinfo/announcement/",
        "Host": "query.sse.com.cn",
    },
    "szse": {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.szse.cn/disclosure/listed/notice/index.html",
        "Origin": "https://www.szse.cn",
    },
    "bse": {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.bse.cn/disclosure/announcement.html",
        "Origin": "https://www.bse.cn",
    },
    "stats_gov": {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://data.stats.gov.cn/easyquery.htm?cn=A01",
        "X-Requested-With": "XMLHttpRequest",
    },
}

SITE_DELAY_RANGES = {
    "eastmoney": (0.4, 1.0),
    "sse": (0.8, 1.6),
    "szse": (0.8, 1.6),
    "bse": (0.8, 1.8),
    "stats_gov": (1.0, 2.0),
}

BLOCK_HINTS = (
    "403 forbidden",
    "429",
    "captcha",
    "验证码",
    "访问过于频繁",
    "waf",
    "forbidden",
    "acl",
)


@dataclass(slots=True)
class CrawlerRuntimeConfig:
    enable_playwright_fallback: bool = False
    retry_times: int = 3
    backoff_base: float = 0.8
    min_delay: float = 0.6
    max_delay: float = 1.5
    use_random_ua: bool = True
    source_mode: str = "auto"
    timeout: int = 30

    @classmethod
    def from_settings(cls, **overrides) -> "CrawlerRuntimeConfig":
        settings = get_settings()
        data = {
            "enable_playwright_fallback": settings.crawler_enable_playwright_fallback,
            "retry_times": settings.crawler_retry_times,
            "backoff_base": settings.crawler_backoff_base,
            "min_delay": settings.crawler_min_delay,
            "max_delay": settings.crawler_max_delay,
            "use_random_ua": settings.crawler_use_random_ua,
            "source_mode": settings.crawler_source_mode,
        }
        data.update({key: value for key, value in overrides.items() if value is not None})
        return cls(**data)


class CrawlRequestError(RuntimeError):
    def __init__(self, error_type: str, message: str, *, status_code: int | None = None, strategy: str | None = None) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.status_code = status_code
        self.strategy = strategy


def build_crawl_result(
    *,
    success: bool,
    source: str,
    strategy: str,
    data: Any | None = None,
    items: list[dict] | None = None,
    warnings: list[str] | None = None,
    error_message: str | None = None,
    error_type: str | None = None,
    meta: dict | None = None,
) -> dict:
    result = {
        "success": bool(success),
        "source": source,
        "strategy": strategy,
        "warnings": warnings or [],
        "error_message": error_message,
    }
    if items is not None:
        result["items"] = items
    if data is not None:
        result["data"] = data
    if error_type:
        result["error_type"] = error_type
    if meta:
        result["meta"] = meta
    return result


def load_sample_json(sample_name: str) -> Any:
    sample_path = Path(__file__).resolve().parents[1] / "samples" / sample_name
    return json.loads(sample_path.read_text(encoding="utf-8"))


def strip_jsonp(payload: str) -> str:
    text = str(payload or "").strip()
    if not text:
        return text
    if text[0] == "{" or text[0] == "[":
        return text
    left = text.find("(")
    right = text.rfind(")")
    if left >= 0 and right > left:
        return text[left + 1:right].strip()
    return text


class SiteHttpClient:
    def __init__(self, site: str, *, config: CrawlerRuntimeConfig | None = None) -> None:
        self.site = site
        self.config = config or CrawlerRuntimeConfig.from_settings()
        self._requests_session = self._build_requests_session()
        self._curl_session = self._build_curl_session()
        self._last_request_at = 0.0

    def get_json(
        self,
        url: str,
        *,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: int | None = None,
        strategy: str = "auto",
        jsonp: bool = False,
    ) -> tuple[dict | list, str]:
        text, strategy_used = self.get_text(
            url,
            params=params,
            headers=headers,
            timeout=timeout,
            strategy=strategy,
        )
        try:
            return json.loads(strip_jsonp(text) if jsonp else text), strategy_used
        except json.JSONDecodeError as exc:
            raise CrawlRequestError(
                "interface_invalid",
                f"{self.site} returned non-JSON content",
                strategy=strategy_used,
            ) from exc

    def post_json(
        self,
        url: str,
        *,
        params: dict | None = None,
        data: Any | None = None,
        json_body: Any | None = None,
        headers: dict | None = None,
        timeout: int | None = None,
        strategy: str = "auto",
        jsonp: bool = False,
    ) -> tuple[dict | list, str]:
        text, strategy_used = self.post_text(
            url,
            params=params,
            data=data,
            json_body=json_body,
            headers=headers,
            timeout=timeout,
            strategy=strategy,
        )
        try:
            return json.loads(strip_jsonp(text) if jsonp else text), strategy_used
        except json.JSONDecodeError as exc:
            raise CrawlRequestError(
                "interface_invalid",
                f"{self.site} returned non-JSON content",
                strategy=strategy_used,
            ) from exc

    def get_text(
        self,
        url: str,
        *,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: int | None = None,
        strategy: str = "auto",
    ) -> tuple[str, str]:
        strategies = self._resolve_strategies(strategy)
        last_error: CrawlRequestError | None = None
        for candidate in strategies:
            try:
                return self._request_with_retry(
                    "GET",
                    url,
                    params=params,
                    data=None,
                    json_body=None,
                    headers=headers,
                    timeout=timeout,
                    strategy=candidate,
                ), candidate
            except CrawlRequestError as exc:
                last_error = exc
        if last_error is None:
            raise CrawlRequestError("network_error", f"{self.site} request failed without details")
        raise last_error

    def post_text(
        self,
        url: str,
        *,
        params: dict | None = None,
        data: Any | None = None,
        json_body: Any | None = None,
        headers: dict | None = None,
        timeout: int | None = None,
        strategy: str = "auto",
    ) -> tuple[str, str]:
        strategies = self._resolve_strategies(strategy)
        last_error: CrawlRequestError | None = None
        for candidate in strategies:
            try:
                return self._request_with_retry(
                    "POST",
                    url,
                    params=params,
                    data=data,
                    json_body=json_body,
                    headers=headers,
                    timeout=timeout,
                    strategy=candidate,
                ), candidate
            except CrawlRequestError as exc:
                last_error = exc
        if last_error is None:
            raise CrawlRequestError("network_error", f"{self.site} request failed without details")
        raise last_error

    def _resolve_strategies(self, strategy: str) -> list[str]:
        if strategy == "playwright":
            return ["playwright"]
        if strategy == "requests":
            return ["requests"]
        strategies = ["requests"]
        if self.config.enable_playwright_fallback:
            strategies.append("playwright")
        return strategies

    def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        params: dict | None,
        data: Any | None,
        json_body: Any | None,
        headers: dict | None,
        timeout: int | None,
        strategy: str,
    ) -> str:
        attempts = max(int(self.config.retry_times), 1)
        last_error: CrawlRequestError | None = None
        for attempt in range(attempts):
            self._throttle()
            try:
                return self._perform_request(
                    method,
                    url,
                    params=params,
                    data=data,
                    json_body=json_body,
                    headers=headers,
                    timeout=timeout,
                    strategy=strategy,
                )
            except CrawlRequestError as exc:
                last_error = exc
                if not self._should_retry(exc, attempt, attempts):
                    break
                self._sleep_backoff(attempt)
        if last_error is None:
            raise CrawlRequestError("network_error", f"{self.site} request failed without details", strategy=strategy)
        raise last_error

    def _perform_request(
        self,
        method: str,
        url: str,
        *,
        params: dict | None,
        data: Any | None,
        json_body: Any | None,
        headers: dict | None,
        timeout: int | None,
        strategy: str,
    ) -> str:
        merged_headers = self._build_headers(headers)
        timeout = timeout or self.config.timeout

        if strategy == "playwright":
            return self._fetch_with_playwright(
                method,
                url,
                params=params,
                data=data,
                json_body=json_body,
                headers=merged_headers,
                timeout=timeout,
            )

        session = self._curl_session or self._requests_session
        try:
            request_callable = getattr(session, method.lower(), None)
            if request_callable is None:
                raise CrawlRequestError("interface_invalid", f"unsupported HTTP method: {method}", strategy=strategy)
            response = request_callable(
                url,
                params=params,
                data=data,
                json=json_body,
                headers=merged_headers,
                timeout=timeout,
            )
        except RequestException as exc:
            raise CrawlRequestError("network_error", f"{self.site} network error: {exc}", strategy=strategy) from exc
        except Exception as exc:
            raise CrawlRequestError("network_error", f"{self.site} unexpected request error: {exc}", strategy=strategy) from exc

        if response.status_code >= 400:
            raise self._response_error(response, strategy=strategy)
        return str(response.text or "")

    def _fetch_with_playwright(
        self,
        method: str,
        url: str,
        *,
        params: dict | None,
        data: Any | None,
        json_body: Any | None,
        headers: dict,
        timeout: int,
    ) -> str:
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise CrawlRequestError(
                "playwright_unavailable",
                "playwright fallback is not installed",
                strategy="playwright",
            ) from exc

        request_url = requests.Request(method.upper(), url, params=params).prepare().url
        timeout_ms = max(int(timeout), 1) * 1000
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(extra_http_headers=headers)
                page = context.new_page()
                response = None
                if method.upper() == "GET":
                    response = page.goto(request_url, wait_until="domcontentloaded", timeout=timeout_ms)
                    content = page.content()
                else:
                    page.goto(headers.get("Referer") or url, wait_until="domcontentloaded", timeout=timeout_ms)
                    response_payload = page.evaluate(
                        """
                        async ({ requestUrl, method, headers, data, jsonBody }) => {
                            const body = jsonBody !== null && jsonBody !== undefined
                                ? JSON.stringify(jsonBody)
                                : data;
                            const response = await fetch(requestUrl, {
                                method,
                                credentials: 'include',
                                headers,
                                body,
                            });
                            return {
                                ok: response.ok,
                                status: response.status,
                                text: await response.text(),
                            };
                        }
                        """,
                        {
                            "requestUrl": request_url,
                            "method": method.upper(),
                            "headers": headers,
                            "data": data,
                            "jsonBody": json_body,
                        },
                    )
                    status_code = int(response_payload.get("status") or 0)
                    if not response_payload.get("ok"):
                        raise CrawlRequestError(
                            self._classify_error_type(status_code=status_code, body=response_payload.get("text")),
                            f"{self.site} playwright HTTP {status_code}",
                            status_code=status_code,
                            strategy="playwright",
                        )
                    content = str(response_payload.get("text") or "")
                browser.close()
        except PlaywrightTimeoutError as exc:
            raise CrawlRequestError("network_error", f"{self.site} playwright timeout: {exc}", strategy="playwright") from exc
        except PlaywrightError as exc:
            raise CrawlRequestError("network_error", f"{self.site} playwright error: {exc}", strategy="playwright") from exc
        except Exception as exc:
            raise CrawlRequestError("network_error", f"{self.site} playwright unexpected error: {exc}", strategy="playwright") from exc

        if response is not None and response.status >= 400:
            raise CrawlRequestError(
                self._classify_error_type(status_code=response.status, body=content),
                f"{self.site} playwright HTTP {response.status}",
                status_code=response.status,
                strategy="playwright",
            )
        return content

    def _response_error(self, response, *, strategy: str) -> CrawlRequestError:
        body = str(response.text or "")[:240]
        error_type = self._classify_error_type(status_code=response.status_code, body=body)
        message = f"{self.site} HTTP {response.status_code}: {body or 'empty response body'}"
        return CrawlRequestError(error_type, message, status_code=response.status_code, strategy=strategy)

    def _classify_error_type(self, *, status_code: int | None, body: str | None) -> str:
        text = str(body or "").lower()
        if status_code in {400, 422}:
            return "parameter_error"
        if status_code in {403, 429} or any(hint in text for hint in BLOCK_HINTS):
            return "blocked"
        if status_code in {404, 405}:
            return "interface_invalid"
        if status_code is not None and status_code >= 500:
            return "network_error"
        return "structure_changed"

    def _should_retry(self, exc: CrawlRequestError, attempt: int, attempts: int) -> bool:
        if attempt >= attempts - 1:
            return False
        return exc.error_type in {"blocked", "network_error"}

    def _sleep_backoff(self, attempt: int) -> None:
        delay = float(self.config.backoff_base) * (2 ** attempt)
        delay += random.uniform(0.0, max(float(self.config.backoff_base), 0.1))
        time.sleep(delay)

    def _throttle(self) -> None:
        site_min, site_max = SITE_DELAY_RANGES.get(self.site, (self.config.min_delay, self.config.max_delay))
        min_delay = max(float(self.config.min_delay), float(site_min))
        max_delay = max(min_delay, float(self.config.max_delay), float(site_max))
        now = time.monotonic()
        wait_for = random.uniform(min_delay, max_delay)
        elapsed = now - self._last_request_at
        if elapsed < wait_for:
            time.sleep(wait_for - elapsed)
        self._last_request_at = time.monotonic()

    def _build_headers(self, headers: dict | None) -> dict:
        base_headers = dict(SITE_HEADERS.get(self.site, {}))
        base_headers.setdefault("Accept-Encoding", "gzip, deflate, br")
        base_headers["User-Agent"] = self._pick_user_agent()
        if headers:
            base_headers.update(headers)
        return base_headers

    def _pick_user_agent(self) -> str:
        if self.config.use_random_ua:
            return random.choice(USER_AGENTS)
        return USER_AGENTS[0]

    def _build_requests_session(self) -> requests.Session:
        session = requests.Session()
        adapter = HTTPAdapter(pool_connections=8, pool_maxsize=8)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _build_curl_session(self):
        if curl_requests is None:
            return None
        try:
            return curl_requests.Session(impersonate="chrome124")
        except Exception:
            return None


__all__ = [
    "CrawlerRuntimeConfig",
    "CrawlRequestError",
    "SiteHttpClient",
    "build_crawl_result",
    "load_sample_json",
    "strip_jsonp",
]