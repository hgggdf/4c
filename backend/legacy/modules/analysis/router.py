"""legacy compat: 旧分析路由路径转发到 app.router.analysis。"""

from app.router.analysis import router

__all__ = ["router"]
