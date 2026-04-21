"""legacy compat: 旧聊天路由路径转发到 app.router.chat。"""

from app.router.chat import router

__all__ = ["router"]
