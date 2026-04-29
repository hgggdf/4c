from __future__ import annotations

import logging
import time
from typing import Any, Iterator

from openai import OpenAI

from config import get_settings

logger = logging.getLogger(__name__)


class KimiClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.kimi_api_key.strip()
        self.base_url = settings.kimi_base_url.strip()
        self.model = settings.kimi_model.strip()

    def is_configured(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    def _make_client(self) -> OpenAI:
        return OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        if not self.is_configured():
            raise RuntimeError(
                "Kimi is not configured. Set KIMI_API_KEY, KIMI_BASE_URL, and KIMI_MODEL in .env."
            )

        client = self._make_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 1.0,
        max_tokens: int = 2048,
        max_retries: int = 2,
    ) -> Iterator[str]:
        if not self.is_configured():
            raise RuntimeError(
                "Kimi is not configured. Set KIMI_API_KEY, KIMI_BASE_URL, and KIMI_MODEL in .env."
            )

        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                client = self._make_client()
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                )
                for chunk in response:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield delta.content
                return
            except Exception as exc:
                last_exc = exc
                if attempt < max_retries:
                    wait = 2 * (attempt + 1)
                    logger.warning("Kimi stream attempt %d failed (%s), retrying in %ds...", attempt + 1, exc, wait)
                    time.sleep(wait)
                else:
                    raise


__all__ = ["KimiClient"]
