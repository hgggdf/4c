"""
ingest_center / http_client.py
=============================

Service 调用适配层模块（原 HTTP 客户端已废弃）。

职责：
    封装对后端 service 层的直接调用，提供统一的调用入口。
    不再通过 /api/ingest/* HTTP 路由，而是直接在进程内调用 IngestGatewayService / MacroWriteService 等方法。

返回结构：
    {
        "ok": bool,
        "response_data": dict | None,
        "error_message": str | None,
        "error_code": str | None,
        "trace_id": str | None,
        "warnings": list | None,
    }
"""

import traceback
from typing import Any, Dict

from app.service.write_requests import (
    BatchItemsRequest,
    IngestAnnouncementPackageRequest,
    IngestCompanyPackageRequest,
    IngestFinancialPackageRequest,
    IngestNewsPackageRequest,
)

from .service_runtime import get_container


def call_service(action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据 action 名称直接调用后端 service 层。

    Args:
        action: service action 名称，如 "ingest_company_package"。
        payload: 请求体字典，结构与对应 Request dataclass 一致。

    Returns:
        统一响应结构。
    """
    container = get_container()

    try:
        if action == "ingest_company_package":
            req = IngestCompanyPackageRequest(**payload)
            result = container.ingest.ingest_company_package(req)
        elif action == "ingest_financial_package":
            req = IngestFinancialPackageRequest(**payload)
            result = container.ingest.ingest_financial_package(req)
        elif action == "ingest_announcement_package":
            req = IngestAnnouncementPackageRequest(**payload)
            result = container.ingest.ingest_announcement_package(req)
        elif action == "ingest_news_package":
            req = IngestNewsPackageRequest(**payload)
            result = container.ingest.ingest_news_package(req)
        elif action == "batch_upsert_macro_indicators":
            req = BatchItemsRequest(**payload)
            result = container.macro_write.batch_upsert_macro_indicators(req)
        else:
            return {
                "ok": False,
                "response_data": None,
                "error_message": f"unknown service action: {action}",
                "error_code": "UNKNOWN_ACTION",
                "trace_id": None,
                "warnings": [],
            }

        return {
            "ok": result.success,
            "response_data": result.data,
            "error_message": result.message if not result.success else None,
            "error_code": result.error_code,
            "trace_id": result.trace_id,
            "warnings": result.warnings,
        }
    except Exception as exc:
        exc_type = type(exc).__name__
        exc_str = str(exc) if str(exc) else "(no message)"
        tb_text = traceback.format_exc()
        # 限制 traceback 长度，避免 receipt 过大
        if len(tb_text) > 3000:
            tb_text = tb_text[:3000] + "\n... (traceback truncated)"

        return {
            "ok": False,
            "response_data": None,
            "error_message": f"[{exc_type}] {exc_str}",
            "error_code": "SERVICE_EXCEPTION",
            "trace_id": None,
            "warnings": [tb_text],
        }
