from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any


def normalize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [normalize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: normalize_value(v) for k, v in value.items()}
    return value


def model_to_dict(obj: Any, fields: list[str] | tuple[str, ...]) -> dict[str, Any]:
    return {field: normalize_value(getattr(obj, field, None)) for field in fields}
