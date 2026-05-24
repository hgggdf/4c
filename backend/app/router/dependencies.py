"""路由层依赖注入。"""

from functools import lru_cache

from app.service import ServiceContainer


@lru_cache(maxsize=1)
def get_container() -> ServiceContainer:
	"""返回全局缓存的服务容器。"""
	return ServiceContainer.build_default()


__all__ = ["get_container"]