"""正式路由包。"""

from .analysis import router as analysis_router
from .announcement import router as announcement_router
from .announcement_write import router as announcement_write_router
from .cache import router as cache_router
from .chat import router as chat_router
from .company import router as company_router
from .company_write import router as company_write_router
from .financial import router as financial_router
from .financial_write import router as financial_write_router
from .ingest import router as ingest_router
from .macro import router as macro_router
from .macro_write import router as macro_write_router
from .maintenance import router as maintenance_router
from .news import router as news_router
from .news_write import router as news_write_router
from .retrieval import router as retrieval_router
from .stock import router as stock_router

__all__ = [
	"analysis_router",
	"announcement_router",
	"announcement_write_router",
	"cache_router",
	"chat_router",
	"company_router",
	"company_write_router",
	"financial_router",
	"financial_write_router",
	"ingest_router",
	"macro_router",
	"macro_write_router",
	"maintenance_router",
	"news_router",
	"news_write_router",
	"retrieval_router",
	"stock_router",
]