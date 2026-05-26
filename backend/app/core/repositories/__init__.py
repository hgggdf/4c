"""Repository layer.

仓储层。

仓储直接与数据库（ORM / SQLAlchemy Session）交互，
并暴露面向表或实体的方法。Service 层应将多个仓储组合起来，
形成面向业务的功能。
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
from .pipeline_repository import PipelineRepository
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
    "PipelineRepository",
    "ResearchReportRepository",
    "MacroRepository",
    "MacroWriteRepository",
    "MaintenanceRepository",
    "ChatRepository",
    "CacheRepository",
]
