"""路由层通用适配工具。"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any, Type

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

_ERROR_STATUS_MAP = {
	"VALIDATION_ERROR": 400,
	"NOT_FOUND": 404,
	"CONFLICT": 409,
	"UNAUTHORIZED": 401,
	"FORBIDDEN": 403,
}


def build_request(req_cls: Type[Any], payload: Any) -> Any:
	"""把 Pydantic 请求模型转换为 service 层 dataclass 请求对象。"""
	if hasattr(payload, "model_dump"):
		data = payload.model_dump(exclude_none=True)
	elif isinstance(payload, dict):
		data = {key: value for key, value in payload.items() if value is not None}
	else:
		data = payload
	if is_dataclass(req_cls):
		valid_keys = {f.name for f in fields(req_cls)}
		data = {k: v for k, v in data.items() if k in valid_keys}
	return req_cls(**data)


def service_result_response(result: Any) -> JSONResponse:
	"""把 service 层返回对象统一映射为 HTTP JSON 响应。"""
	if is_dataclass(result):
		status_code = 200 if getattr(result, "success", False) else _ERROR_STATUS_MAP.get(
			getattr(result, "error_code", None),
			500,
		)
		return JSONResponse(status_code=status_code, content=jsonable_encoder(result))
	return JSONResponse(status_code=200, content=jsonable_encoder(result))


__all__ = ["build_request", "service_result_response"]