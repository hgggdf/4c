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

    @staticmethod
    def _build_vision_content(text: str, images: list[str]) -> list[dict[str, Any]]:
        """把文本和 base64 图片列表组合成 Claude vision content blocks。"""
        content: list[dict[str, Any]] = []
        for img_b64 in images:
            # 格式：data:image/png;base64,<data>
            if "," in img_b64:
                media_type_part, data_part = img_b64.split(",", 1)
                media_type = media_type_part.split(":")[1].split(";")[0] if ":" in media_type_part else "image/png"
            else:
                data_part = img_b64
                media_type = "image/png"
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": data_part},
            })
        content.append({"type": "text", "text": text})
        return content

    def chat(
        self,
        messages: list[dict[str, Any]],
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
                system_content = str(msg.get("content") or "")
                continue
            images: list[str] = msg.get("images") or []
            text = str(msg.get("content") or "")
            if images:
                content = self._build_vision_content(text, images)
            else:
                content = text
            user_messages.append({"role": msg["role"], "content": content})

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

    def chat_with_images(
        self,
        question: str,
        images: list[str],
        *,
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        """直接传入图片列表进行视觉分析，返回分析文本。"""
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": question, "images": images})
        return self.chat(messages, max_tokens=max_tokens)


__all__ = ["ClaudeClient"]
