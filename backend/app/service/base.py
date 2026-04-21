from __future__ import annotations

from typing import Any, Callable, TypeVar, cast

from .context import ServiceContext
from .dto import ServiceResult
from .exceptions import ServiceException

T = TypeVar("T")


class BaseService:
    def __init__(self, *, ctx: ServiceContext) -> None:
        self.ctx = ctx

    def _ok(self, data: T | None = None, *, message: str = "", trace_id: str | None = None) -> ServiceResult[T]:
        return ServiceResult.ok(data, message=message, trace_id=trace_id)

    def _handle_exc(self, exc: Exception, *, trace_id: str | None = None) -> ServiceResult[Any]:
        if isinstance(exc, ServiceException):
            return ServiceResult.fail(str(exc), error_code=exc.error_code, trace_id=trace_id)
        if isinstance(exc, (ValueError, TypeError)):
            return ServiceResult.fail(str(exc), error_code="VALIDATION_ERROR", trace_id=trace_id)
        return ServiceResult.fail("internal error", error_code="INTERNAL_ERROR", trace_id=trace_id)

    def _run(self, fn: Callable[[], T | ServiceResult[T]], *, trace_id: str | None = None) -> ServiceResult[T]:
        try:
            result = fn()
            if isinstance(result, ServiceResult):
                if result.trace_id is None:
                    result.trace_id = trace_id
                return result
            return self._ok(cast(T, result), trace_id=trace_id)
        except Exception as exc:  # noqa: BLE001
            return cast(ServiceResult[T], self._handle_exc(exc, trace_id=trace_id))

    def _with_db(self, fn: Callable[[Any], T]) -> T:
        with self.ctx.session() as db:
            return fn(db)
