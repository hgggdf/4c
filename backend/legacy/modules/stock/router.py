"""legacy compat: 旧股票路由路径转发到 app.router.stock。"""

from app.router.stock import router

__all__ = ["router"]
