"""compat package: 旧 service.* 导入路径转发到 legacy/compat/service。"""

from pathlib import Path as _Path

_pkg_dir = _Path(__file__).resolve().parent
_compat_dir = _pkg_dir.parent / "legacy" / "compat" / "service"

__path__ = [str(_pkg_dir)]
if _compat_dir.exists():
    __path__.append(str(_compat_dir))

from .service import (
    AnnouncementService,
    AnnouncementWriteService,
    CacheService,
    ChatService,
    CompanyService,
    CompanyWriteService,
    FinancialService,
    FinancialWriteService,
    IngestGatewayService,
    MacroService,
    MacroWriteService,
    MaintenanceService,
    NewsService,
    NewsWriteService,
    RetrievalService,
    ServiceContainer,
    ServiceContext,
    build_default_context,
)

__all__ = [
    "ServiceContext",
    "build_default_context",
    "ServiceContainer",
    "CompanyService",
    "FinancialService",
    "AnnouncementService",
    "NewsService",
    "MacroService",
    "RetrievalService",
    "ChatService",
    "CacheService",
    "CompanyWriteService",
    "FinancialWriteService",
    "AnnouncementWriteService",
    "MacroWriteService",
    "NewsWriteService",
    "MaintenanceService",
    "IngestGatewayService",
]