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
