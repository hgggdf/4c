"""Backward-compatible entrypoint for the runtime chat dialogue service."""

from app.service.chat_dialogue_service import ChatService

__all__ = ["ChatService"]
