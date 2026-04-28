"""Agent测试 fixtures - 使用独立的测试数据库配置"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 确保可以导入项目模块
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 临时 mock app.core.database.session 避免 import 时触发 MySQL 连接
_original_session_module = sys.modules.get('app.core.database.session')
sys.modules['app.core.database.session'] = MagicMock()

# 现在可以安全导入了
from tests.service.conftest import (  # noqa: F401, E402
    engine,
    session_factory,
    services,
    FakeVectorStore,
)

from app.service.container import ServiceContainer  # noqa: E402
from app.service.context import ServiceContext  # noqa: E402

# 导入完成后恢复原始模块，避免污染其他测试
if _original_session_module is not None:
    sys.modules['app.core.database.session'] = _original_session_module
else:
    del sys.modules['app.core.database.session']


@pytest.fixture(autouse=True)
def _patch_build_default(session_factory):
    """让 ServiceContainer.build_default() 使用测试 SQLite 而非 MySQL"""
    def _build():
        ctx = ServiceContext(
            session_factory=session_factory,
            cache=None,
            vector_store=FakeVectorStore(),
        )
        from app.service.company_service import CompanyService
        from app.service.financial_service import FinancialService
        from app.service.announcement_service import AnnouncementService
        from app.service.news_service import NewsService
        from app.service.macro_service import MacroService
        from app.service.retrieval_service import RetrievalService
        from app.service.chat_service import ChatService
        from app.service.cache_service import CacheService
        from app.service.company_write_service import CompanyWriteService
        from app.service.financial_write_service import FinancialWriteService
        from app.service.announcement_write_service import AnnouncementWriteService
        from app.service.macro_write_service import MacroWriteService
        from app.service.news_write_service import NewsWriteService
        from app.service.maintenance_service import MaintenanceService
        from app.service.ingest_gateway_service import IngestGatewayService

        company = CompanyService(ctx=ctx)
        retrieval = RetrievalService(ctx=ctx, company_service=company)
        cache = CacheService(ctx=ctx)
        cw = CompanyWriteService(ctx=ctx)
        fw = FinancialWriteService(ctx=ctx)
        aw = AnnouncementWriteService(ctx=ctx)
        mw = MacroWriteService(ctx=ctx)
        nw = NewsWriteService(ctx=ctx)
        maintenance = MaintenanceService(ctx=ctx)
        return ServiceContainer(
            ctx=ctx,
            company=company,
            financial=FinancialService(ctx=ctx, company_service=company),
            announcement=AnnouncementService(ctx=ctx, company_service=company),
            news=NewsService(ctx=ctx, company_service=company, retrieval_service=retrieval),
            macro=MacroService(ctx=ctx),
            retrieval=retrieval,
            chat=ChatService(ctx=ctx, company_service=company, cache_service=cache),
            cache=cache,
            company_write=cw,
            financial_write=fw,
            announcement_write=aw,
            macro_write=mw,
            news_write=nw,
            maintenance=maintenance,
            ingest=IngestGatewayService(ctx=ctx, company_write=cw, financial_write=fw, announcement_write=aw, macro_write=mw, news_write=nw),
        )

    with patch.object(ServiceContainer, "build_default", staticmethod(_build)):
        yield
