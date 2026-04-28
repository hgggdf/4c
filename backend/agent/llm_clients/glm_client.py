from __future__ import annotations

import json
from typing import Any

import requests

from config import get_settings


def _normalize_base_url(value: str) -> str:
    base_url = str(value or "").strip()
    if not base_url:
        return ""
    if base_url.endswith("/chat/completions"):
        return base_url
    return f"{base_url.rstrip('/')}/chat/completions"


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, dict):
        for key in ("text", "content", "reasoning_content"):
            text = _extract_text_content(content.get(key))
            if text:
                return text
        return ""
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = str(item.get("text") or "").strip()
                if text:
                    parts.append(text)
            elif isinstance(item, str):
                text = item.strip()
                if text:
                    parts.append(text)
        return "\n".join(parts).strip()
    return ""


def _sanitize_text(value: str, *, limit: int = 240) -> str:
    text = str(value or "").replace("\n", " ").replace("\r", " ").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _extract_choice_text(choice: dict[str, Any]) -> str:
    message = choice.get("message") or {}
    if isinstance(message, dict):
        for key in ("content", "reasoning_content"):
            text = _extract_text_content(message.get(key))
            if text:
                return text

    delta = choice.get("delta") or {}
    if isinstance(delta, dict):
        for key in ("content", "reasoning_content"):
            text = _extract_text_content(delta.get(key))
            if text:
                return text

    return _extract_text_content(choice.get("output_text"))


class GLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.glm_api_key.strip()
        self.base_url = _normalize_base_url(settings.glm_base_url)
        self.model = settings.glm_model.strip()
        self.timeout_seconds = 120

    def is_configured(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 500,
    ) -> str:
        if not self.is_configured():
            raise RuntimeError("GLM is not configured. Set GLM_API_KEY, GLM_BASE_URL, and GLM_MODEL in backend/.env.")

        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "thinking": {"type": "disabled"},
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=self.timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(f"timeout after {self.timeout_seconds}s") from exc
        except requests.exceptions.RequestException as exc:
            detail = _sanitize_text(str(exc))
            raise RuntimeError(f"request_error {exc.__class__.__name__}: {detail}") from exc

        if response.status_code >= 400:
            detail = _sanitize_text(response.text)
            raise RuntimeError(f"status_code={response.status_code} response={detail}")

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise RuntimeError("GLM returned a non-JSON response.") from exc

        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            text = _extract_choice_text(choices[0] or {})
            if text:
                return text

        text = _extract_text_content(payload.get("output_text"))
        if text:
            return text

        data = payload.get("data")
        if isinstance(data, list) and data:
            text = _extract_text_content(data[0].get("content"))
            if text:
                return text

        raise RuntimeError("GLM response did not contain any text content.")


__all__ = ["GLMClient"]