from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def safe_to_dict(value: Any) -> Any:
    try:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if is_dataclass(value):
            return safe_to_dict(asdict(value))
        if isinstance(value, list):
            return [safe_to_dict(item) for item in value]
        if isinstance(value, dict):
            return {str(key): safe_to_dict(item) for key, item in value.items()}
        if hasattr(value, "model_dump"):
            try:
                return safe_to_dict(value.model_dump())
            except Exception:
                pass
        if hasattr(value, "dict"):
            try:
                return safe_to_dict(value.dict())
            except Exception:
                pass
        return {"repr": str(value)}
    except Exception:
        try:
            return {"repr": str(value)}
        except Exception:
            return {"repr": "<unserializable>"}


def to_float(v: Any, default: float | None = None) -> float | None:
    if v is None:
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def generate_uid_md5(*parts: Any) -> str:
    import hashlib

    key = "-".join(str(p) for p in parts)
    return hashlib.md5(key.encode()).hexdigest()
