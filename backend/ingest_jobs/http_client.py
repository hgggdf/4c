"""
HTTP 客户端
封装 POST/GET 请求，带错误处理和重试
不调用任何 ingest API，直接连接后端
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import requests

from .config import get_config


@dataclass
class HttpResponse:
    """HTTP 响应封装"""
    status_code: int
    data: dict | list | None
    error: str | None = None
    success: bool = False
    elapsed_ms: int = 0

    @property
    def is_success(self) -> bool:
        return self.success and 200 <= self.status_code < 300


class HttpClient:
    """
    HTTP 客户端，带重试和超时
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
        retry_times: int | None = None,
    ):
        config = get_config()
        self.base_url = (base_url or config.api_base_url).rstrip("/")
        self.timeout = timeout or config.api_timeout
        self.retry_times = retry_times or config.api_retry_times
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def post(
        self,
        endpoint: str,
        payload: dict,
        *,
        params: dict | None = None,
    ) -> HttpResponse:
        """
        POST JSON 到指定 endpoint
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        start = time.time()

        for attempt in range(1, self.retry_times + 1):
            try:
                resp = self.session.post(
                    url,
                    json=payload,
                    params=params,
                    timeout=self.timeout,
                )
                elapsed_ms = int((time.time() - start) * 1000)

                try:
                    data = resp.json()
                except Exception:
                    data = {"raw_text": resp.text[:200]}

                success = 200 <= resp.status_code < 300
                error = None if success else f"HTTP {resp.status_code}: {resp.reason}"

                return HttpResponse(
                    status_code=resp.status_code,
                    data=data,
                    error=error,
                    success=success,
                    elapsed_ms=elapsed_ms,
                )

            except requests.exceptions.Timeout:
                error = f"请求超时（第{attempt}次）"
                if attempt == self.retry_times:
                    elapsed_ms = int((time.time() - start) * 1000)
                    return HttpResponse(
                        status_code=0,
                        data=None,
                        error=error,
                        success=False,
                        elapsed_ms=elapsed_ms,
                    )
                time.sleep(1 * attempt)

            except requests.exceptions.ConnectionError as exc:
                error = f"连接失败（第{attempt}次）: {exc}"
                if attempt == self.retry_times:
                    elapsed_ms = int((time.time() - start) * 1000)
                    return HttpResponse(
                        status_code=0,
                        data=None,
                        error=error,
                        success=False,
                        elapsed_ms=elapsed_ms,
                    )
                time.sleep(1 * attempt)

            except Exception as exc:
                elapsed_ms = int((time.time() - start) * 1000)
                return HttpResponse(
                    status_code=0,
                    data=None,
                    error=f"未知错误: {exc}",
                    success=False,
                    elapsed_ms=elapsed_ms,
                )

        # 不应该到这里
        elapsed_ms = int((time.time() - start) * 1000)
        return HttpResponse(
            status_code=0,
            data=None,
            error="重试耗尽",
            success=False,
            elapsed_ms=elapsed_ms,
        )

    def get(self, endpoint: str, *, params: dict | None = None) -> HttpResponse:
        """GET 请求"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        start = time.time()

        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            elapsed_ms = int((time.time() - start) * 1000)

            try:
                data = resp.json()
            except Exception:
                data = {"raw_text": resp.text[:200]}

            success = 200 <= resp.status_code < 300
            return HttpResponse(
                status_code=resp.status_code,
                data=data,
                error=None if success else f"HTTP {resp.status_code}",
                success=success,
                elapsed_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = int((time.time() - start) * 1000)
            return HttpResponse(
                status_code=0,
                data=None,
                error=str(exc),
                success=False,
                elapsed_ms=elapsed_ms,
            )
