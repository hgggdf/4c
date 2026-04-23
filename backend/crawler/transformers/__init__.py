"""
OpenClaw Transform 模块
职责：raw → staging → manifest → quality_report
不调用任何 ingest API，不连接数据库
"""

from .stock_daily_transformer import StockDailyTransformer
from .announcement_transformer import AnnouncementTransformer
from .research_report_transformer import ResearchReportTransformer
from .macro_transformer import MacroTransformer
from .company_transformer import CompanyTransformer
from .patent_transformer import PatentTransformer

# patent 只能 raw→staging，禁止入库
TRANSFORMER_REGISTRY = {
    "stock_daily": StockDailyTransformer,
    "announcement_raw": AnnouncementTransformer,
    "research_report": ResearchReportTransformer,
    "macro": MacroTransformer,
    "company": CompanyTransformer,
    "patent": PatentTransformer,  # 只生成 raw/staging，不允许入库
}


def get_transformer(data_category: str):
    """根据 data_category 获取对应的 transformer"""
    cls = TRANSFORMER_REGISTRY.get(data_category)
    if cls is None:
        raise ValueError(f"Unsupported data_category: {data_category}")
    return cls
