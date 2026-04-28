"""Repository layer.

Repositories directly interact with the database (ORM / SQLAlchemy Session)
and expose table/entity oriented methods. Services should compose repositories
into business-oriented capabilities.
"""

from .announcement_repository import AnnouncementRepository
from .announcement_write_repository import AnnouncementWriteRepository
from .base import BaseRepository
from .cache_repository import CacheRepository
from .chat_repository import ChatRepository
from .company_repository import CompanyRepository
from .company_write_repository import CompanyWriteRepository
from .financial_repository import FinancialRepository
from .financial_write_repository import FinancialWriteRepository
from .macro_repository import MacroRepository
from .macro_write_repository import MacroWriteRepository
from .maintenance_repository import MaintenanceRepository
from .news_repository import NewsRepository
from .news_write_repository import NewsWriteRepository
from .research_report_repository import ResearchReportRepository

__all__ = [
    "BaseRepository",
    "CompanyRepository",
    "CompanyWriteRepository",
    "FinancialRepository",
    "FinancialWriteRepository",
    "AnnouncementRepository",
    "AnnouncementWriteRepository",
    "NewsRepository",
    "NewsWriteRepository",
    "ResearchReportRepository",
    "MacroRepository",
    "MacroWriteRepository",
    "MaintenanceRepository",
    "ChatRepository",
    "CacheRepository",
]
