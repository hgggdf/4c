"""
ingest_center / service_runtime.py
=================================

Service 运行时容器管理模块。

职责：
    在 ingest_center 进程内构建并缓存 ServiceContainer，
    供 dispatcher / http_client（service 适配层）直接调用后端 service 层。

注意：
    复用 app/service/container.py 中已有的 ServiceContainer.build_default() 方法。
"""

from __future__ import annotations

from typing import Optional

from app.service import ServiceContainer

_CONTAINER: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """
    获取（或懒加载）ServiceContainer 单例。

    Returns:
        配置好的 ServiceContainer 实例。
    """
    global _CONTAINER
    if _CONTAINER is None:
        _CONTAINER = ServiceContainer.build_default()
    return _CONTAINER
