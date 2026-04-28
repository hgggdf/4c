from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol


class CacheAdapter(Protocol):
    def get_json(self, key: str) -> dict | None: ...
    def set_json(self, key: str, value: dict, *, ttl_seconds: int) -> None: ...
    def delete(self, key: str) -> bool: ...


@dataclass(slots=True)
class InMemoryTTLCacheAdapter:
    _items: dict[str, tuple[float, dict]]

    def __init__(self) -> None:
        self._items = {}

    def get_json(self, key: str) -> dict | None:
        now = time.monotonic()
        item = self._items.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at and expires_at <= now:
            self._items.pop(key, None)
            return None
        return dict(value)

    def set_json(self, key: str, value: dict, *, ttl_seconds: int) -> None:
        expires_at = time.monotonic() + max(0, int(ttl_seconds))
        self._items[key] = (expires_at, dict(value))

    def delete(self, key: str) -> bool:
        return self._items.pop(key, None) is not None


def build_cache_key(*parts: Any) -> str:
    return ":".join(str(p) for p in parts if p is not None and str(p) != "")
