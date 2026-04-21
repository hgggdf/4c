"""正式路由包。"""

from .analysis import router as analysis_router
from .chat import router as chat_router
from .stock import router as stock_router

__all__ = ["analysis_router", "chat_router", "stock_router"]