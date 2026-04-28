from __future__ import annotations

import re

from .exceptions import ValidationException

_STOCK_CODE_RE = re.compile(r"^[0-9]{6}$")


def require_non_empty(value: str | None, field_name: str) -> str:
    if value is None or not str(value).strip():
        raise ValidationException(f"{field_name} is required")
    return str(value).strip()


def require_positive_int(value: int, field_name: str) -> int:
    if value <= 0:
        raise ValidationException(f"{field_name} must be > 0")
    return value


def require_stock_code(stock_code: str) -> str:
    stock_code = require_non_empty(stock_code, "stock_code")
    if not _STOCK_CODE_RE.match(stock_code):
        raise ValidationException("stock_code must be a 6-digit string")
    return stock_code
