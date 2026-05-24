from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class BaseRequest:
    trace_id: Optional[str] = None
    operator_id: Optional[int] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ServiceResult(Generic[T]):
    success: bool
    message: str = ""
    data: Optional[T] = None
    error_code: Optional[str] = None
    trace_id: Optional[str] = None
    warnings: list[str] = field(default_factory=list)

    @staticmethod
    def ok(data: T | None = None, *, message: str = "", trace_id: str | None = None) -> "ServiceResult[T]":
        return ServiceResult(success=True, message=message, data=data, trace_id=trace_id)

    @staticmethod
    def fail(
        message: str,
        *,
        error_code: str | None = None,
        trace_id: str | None = None,
        warnings: list[str] | None = None,
    ) -> "ServiceResult[T]":
        return ServiceResult(
            success=False,
            message=message,
            error_code=error_code,
            trace_id=trace_id,
            warnings=list(warnings or []),
        )
