from __future__ import annotations

from typing import Any

import anthropic

from config import get_settings


class ClaudeClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.anthropic_api_key.strip()
        self.base_url = settings.anthropic_base_url.strip()
        self.model = settings.claude_model.strip()

    def is_configured(self) -> bool:
        return bool(self.api_key and self.model)

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        if not self.is_configured():
            raise RuntimeError(
                "Claude is not configured. Set ANTHROPIC_API_KEY and CLAUDE_MODEL in backend/.env."
            )

        system_content = ""
        user_messages: list[dict[str, Any]] = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                user_messages.append({"role": msg["role"], "content": msg["content"]})

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_messages,
        }
        if system_content:
            kwargs["system"] = system_content

        client = anthropic.Anthropic(api_key=self.api_key, base_url=self.base_url or None)
        response = client.messages.create(**kwargs)

        for block in response.content:
            if block.type == "text":
                return block.text.strip()

        raise RuntimeError("Claude response did not contain any text content.")


__all__ = ["ClaudeClient"]
