"""OpenClaw统一入库对接路由。

根据openclaw后端统一入库对接说明文档实现的数据入库接口。
支持接收统一JSON格式的数据包，并根据payload_type路由到对应的入库逻辑。
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from app.router.dependencies import get_container
from app.router.utils import service_result_response
from app.service import ServiceContainer

router = APIRouter(prefix="/api/openclaw", tags=["openclaw"])


class OpenClawEnvelope(BaseModel):
    """OpenClaw统一数据包格式"""
    batch_id: str = Field(..., description="批次号，格式：YYYYMMDD_序号")
    task_id: str = Field(..., description="任务ID")
    source: dict = Field(..., description="数据源信息")
    entity: dict = Field(..., description="实体信息")
    document: dict = Field(..., description="原始文档信息")
    payload_type: str = Field(..., description="载荷类型")
    payload: dict = Field(..., description="业务数据载荷")
    processing: dict = Field(..., description="处理状态信息")
    extra: dict = Field(default_factory=dict, description="扩展信息")


@router.post("/ingest")
def ingest_openclaw_data(envelope: OpenClawEnvelope, container: ServiceContainer = Depends(get_container)):
    """OpenClaw统一入库接口

    根据payload_type将数据路由到对应的入库逻辑：
    - company_profile: 公司概况
    - announcement_raw: 公告原始数据
    - announcement_structured: 公告结构化数据
    - news_raw: 新闻原始数据
    - news_structured: 新闻结构化数据
    - financial_statement: 财务报表
    - financial_metric: 财务指标
    - macro_indicator: 宏观指标
    - drug_event: 药品事件
    - procurement_event: 集采事件
    - trial_event: 临床试验事件
    - regulatory_risk_event: 监管风险事件
    - stock_daily: 股票日行情
    """

    payload_type = envelope.payload_type

    try:
        if payload_type == "company_profile":
            return _ingest_company_profile(envelope, container)
        elif payload_type == "announcement_raw":
            return _ingest_announcement_raw(envelope, container)
        elif payload_type == "announcement_structured":
            return _ingest_announcement_structured(envelope, container)
        elif payload_type == "news_raw":
            return _ingest_news_raw(envelope, container)
        elif payload_type == "news_structured":
            return _ingest_news_structured(envelope, container)
        elif payload_type == "financial_statement":
            return _ingest_financial_statement(envelope, container)
        elif payload_type == "financial_metric":
            return _ingest_financial_metric(envelope, container)
        elif payload_type == "macro_indicator":
            return _ingest_macro_indicator(envelope, container)
        elif payload_type == "drug_event":
            return _ingest_drug_event(envelope, container)
        elif payload_type == "procurement_event":
            return _ingest_procurement_event(envelope, container)
        elif payload_type == "trial_event":
            return _ingest_trial_event(envelope, container)
        elif payload_type == "regulatory_risk_event":
            return _ingest_regulatory_risk_event(envelope, container)
        elif payload_type == "stock_daily":
            return _ingest_stock_daily(envelope, container)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported payload_type: {payload_type}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {str(e)}")


def _ingest_company_profile(envelope: OpenClawEnvelope, container: ServiceContainer):
    """公司概况入库"""
    from app.service.write_requests import UpsertCompanyMasterRequest, UpsertCompanyProfileRequest

    entity = envelope.entity
    payload = envelope.payload
    source = envelope.source
    stock_code = entity.get("stock_code", "")

    result = {}

    master_req = UpsertCompanyMasterRequest(
        stock_code=stock_code,
        stock_name=entity.get("stock_name", ""),
        industry_level1=entity.get("industry_code"),
        industry_level2=entity.get("industry_name"),
        source_type=source.get("source_type"),
        source_url=source.get("source_url"),
    )
    master_result = container.company_write.upsert_company_master(master_req)
    if not master_result.success:
        raise ValueError(master_result.message)
    result["company_master"] = master_result.data

    profile_req = UpsertCompanyProfileRequest(
        stock_code=stock_code,
        business_summary=payload.get("business_summary"),
        core_products_json=payload.get("core_products_json"),
        main_segments_json=payload.get("main_segments_json"),
        market_position=payload.get("market_position"),
        management_summary=payload.get("management_summary"),
        sync_vector_index=False,
    )
    profile_result = container.company_write.upsert_company_profile(profile_req)
    if not profile_result.success:
        raise ValueError(profile_result.message)
    result["company_profile"] = profile_result.data

    from app.service.dto import ServiceResult
    return service_result_response(ServiceResult(success=True, data=result))


def _ingest_announcement_raw(envelope: OpenClawEnvelope, container: ServiceContainer):
    """公告原始数据入库"""
    from app.service.write_requests import IngestAnnouncementPackageRequest

    entity = envelope.entity
    payload = envelope.payload
    document = envelope.document
    source = envelope.source

    raw_announcement = {
        "stock_code": entity.get("stock_code", ""),
        "title": document.get("title", ""),
        "publish_date": document.get("publish_time", "").split("T")[0] if document.get("publish_time") else None,
        "announcement_type": payload.get("announcement_type"),
        "exchange": payload.get("exchange"),
        "content": payload.get("content"),
        "source_url": source.get("source_url"),
        "source_type": source.get("source_type"),
        "file_hash": document.get("file_hash"),
    }

    req = IngestAnnouncementPackageRequest(
        raw_announcements=[raw_announcement],
        sync_vector_index=False
    )

    return service_result_response(container.ingest.ingest_announcement_package(req))


def _ingest_announcement_structured(envelope: OpenClawEnvelope, container: ServiceContainer):
    """公告结构化数据入库"""
    from app.service.write_requests import IngestAnnouncementPackageRequest

    entity = envelope.entity
    payload = envelope.payload
    extra = envelope.extra

    structured_announcement = {
        "stock_code": entity.get("stock_code", ""),
        "announcement_id": extra.get("announcement_id"),
        "category": payload.get("category"),
        "summary_text": payload.get("summary_text"),
        "key_fields_json": payload.get("key_fields_json"),
        "signal_type": payload.get("signal_type"),
        "risk_level": payload.get("risk_level"),
    }

    req = IngestAnnouncementPackageRequest(
        structured_announcements=[structured_announcement]
    )

    return service_result_response(container.ingest.ingest_announcement_package(req))


def _ingest_news_raw(envelope: OpenClawEnvelope, container: ServiceContainer):
    """新闻原始数据入库"""
    from app.service.write_requests import IngestNewsPackageRequest

    payload = envelope.payload
    document = envelope.document
    source = envelope.source

    news_raw = {
        "news_uid": payload.get("news_uid", ""),
        "title": document.get("title", ""),
        "publish_time": document.get("publish_time"),
        "source_name": source.get("source_name"),
        "source_url": source.get("source_url"),
        "author_name": payload.get("author_name"),
        "content": payload.get("content"),
        "news_type": payload.get("news_type"),
        "language": document.get("language", "zh"),
        "file_hash": document.get("file_hash"),
    }

    req = IngestNewsPackageRequest(
        news_raw=[news_raw],
        sync_vector_index=False
    )

    return service_result_response(container.ingest.ingest_news_package(req))


def _ingest_news_structured(envelope: OpenClawEnvelope, container: ServiceContainer):
    """新闻结构化数据入库"""
    from app.service.write_requests import IngestNewsPackageRequest

    payload = envelope.payload

    news_structured = {
        "topic_category": payload.get("topic_category"),
        "summary_text": payload.get("summary_text"),
        "keywords_json": payload.get("keywords_json"),
        "signal_type": payload.get("signal_type"),
        "impact_level": payload.get("impact_level"),
        "impact_horizon": payload.get("impact_horizon"),
        "sentiment_label": payload.get("sentiment_label"),
        "confidence_score": payload.get("confidence_score"),
    }

    req = IngestNewsPackageRequest(
        news_structured=[news_structured]
    )

    return service_result_response(container.ingest.ingest_news_package(req))


def _ingest_financial_statement(envelope: OpenClawEnvelope, container: ServiceContainer):
    """财务报表入库"""
    from app.service.write_requests import IngestFinancialPackageRequest

    entity = envelope.entity
    payload = envelope.payload
    source = envelope.source
    extra = envelope.extra

    statement_type = payload.get("statement_type")
    stock_code = entity.get("stock_code", "")

    base_fields = {
        "stock_code": stock_code,
        "report_date": payload.get("report_date"),
        "fiscal_year": extra.get("fiscal_year"),
        "report_type": extra.get("report_type"),
        "source_type": source.get("source_type"),
        "source_url": source.get("source_url"),
    }

    req_kwargs = {}

    if statement_type == "income_statement":
        income_statement = {
            **base_fields,
            "revenue": payload.get("revenue"),
            "operating_cost": payload.get("operating_cost"),
            "gross_profit": payload.get("gross_profit"),
            "selling_expense": payload.get("selling_expense"),
            "admin_expense": payload.get("admin_expense"),
            "rd_expense": payload.get("rd_expense"),
            "operating_profit": payload.get("operating_profit"),
            "net_profit": payload.get("net_profit"),
            "net_profit_deducted": payload.get("net_profit_deducted"),
            "eps": payload.get("eps"),
        }
        req_kwargs["income_statements"] = [income_statement]
    elif statement_type == "balance_sheet":
        balance_sheet = {
            **base_fields,
            "total_assets": payload.get("total_assets"),
            "total_liabilities": payload.get("total_liabilities"),
            "accounts_receivable": payload.get("accounts_receivable"),
            "inventory": payload.get("inventory"),
            "cash": payload.get("cash"),
            "equity": payload.get("equity"),
            "goodwill": payload.get("goodwill"),
        }
        req_kwargs["balance_sheets"] = [balance_sheet]
    elif statement_type == "cashflow_statement":
        cashflow_statement = {
            **base_fields,
            "operating_cashflow": payload.get("operating_cashflow"),
            "investing_cashflow": payload.get("investing_cashflow"),
            "financing_cashflow": payload.get("financing_cashflow"),
            "free_cashflow": payload.get("free_cashflow"),
        }
        req_kwargs["cashflow_statements"] = [cashflow_statement]
    else:
        raise ValueError(f"Unknown statement_type: {statement_type}")

    req = IngestFinancialPackageRequest(**req_kwargs)
    return service_result_response(container.ingest.ingest_financial_package(req))


def _ingest_financial_metric(envelope: OpenClawEnvelope, container: ServiceContainer):
    """财务指标入库"""
    from app.service.write_requests import IngestFinancialPackageRequest

    entity = envelope.entity
    payload = envelope.payload

    financial_metric = {
        "stock_code": entity.get("stock_code", ""),
        "report_date": payload.get("report_date"),
        "fiscal_year": payload.get("fiscal_year"),
        "metric_name": payload.get("metric_name", ""),
        "metric_value": payload.get("metric_value"),
        "metric_unit": payload.get("metric_unit"),
        "calc_method": payload.get("calc_method"),
        "source_ref_json": payload.get("source_ref_json"),
    }

    req = IngestFinancialPackageRequest(
        financial_metrics=[financial_metric]
    )

    return service_result_response(container.ingest.ingest_financial_package(req))


def _ingest_macro_indicator(envelope: OpenClawEnvelope, container: ServiceContainer):
    """宏观指标入库"""
    from app.service.write_requests import IngestNewsPackageRequest

    payload = envelope.payload
    source = envelope.source

    macro_indicator = {
        "indicator_name": payload.get("indicator_name", ""),
        "period": payload.get("period", ""),
        "value": payload.get("value"),
        "unit": payload.get("unit"),
        "source_type": source.get("source_type"),
        "source_url": source.get("source_url"),
    }

    req = IngestNewsPackageRequest(
        macro_indicators=[macro_indicator]
    )

    return service_result_response(container.ingest.ingest_news_package(req))


def _ingest_drug_event(envelope: OpenClawEnvelope, container: ServiceContainer):
    """药品事件入库"""
    from app.service.write_requests import IngestAnnouncementPackageRequest

    entity = envelope.entity
    payload = envelope.payload
    source = envelope.source
    extra = envelope.extra

    event_kind = payload.get("event_kind")

    if event_kind == "drug_approval":
        drug_approval = {
            "stock_code": entity.get("stock_code", ""),
            "drug_name": payload.get("drug_name"),
            "approval_type": payload.get("approval_type"),
            "approval_date": payload.get("approval_date"),
            "indication": payload.get("indication"),
            "drug_stage": payload.get("drug_stage"),
            "is_innovative_drug": payload.get("is_innovative_drug", 0),
            "review_status": payload.get("review_status"),
            "market_scope": payload.get("market_scope"),
            "source_announcement_id": extra.get("source_announcement_id"),
            "source_type": source.get("source_type"),
            "source_url": source.get("source_url"),
        }
        req = IngestAnnouncementPackageRequest(
            drug_approvals=[drug_approval]
        )
    else:
        raise ValueError(f"Unknown drug event_kind: {event_kind}")

    return service_result_response(container.ingest.ingest_announcement_package(req))


def _ingest_procurement_event(envelope: OpenClawEnvelope, container: ServiceContainer):
    """集采事件入库"""
    from app.service.write_requests import IngestAnnouncementPackageRequest

    entity = envelope.entity
    payload = envelope.payload
    source = envelope.source
    extra = envelope.extra

    procurement_event = {
        "stock_code": entity.get("stock_code", ""),
        "drug_name": payload.get("drug_name"),
        "procurement_round": payload.get("procurement_round"),
        "bid_result": payload.get("bid_result"),
        "price_change_ratio": payload.get("price_change_ratio"),
        "event_date": payload.get("event_date"),
        "impact_summary": payload.get("impact_summary"),
        "source_announcement_id": extra.get("source_announcement_id"),
        "source_type": source.get("source_type"),
        "source_url": source.get("source_url"),
    }

    req = IngestAnnouncementPackageRequest(
        procurement_events=[procurement_event]
    )

    return service_result_response(container.ingest.ingest_announcement_package(req))


def _ingest_trial_event(envelope: OpenClawEnvelope, container: ServiceContainer):
    """临床试验事件入库"""
    from app.service.write_requests import IngestAnnouncementPackageRequest

    entity = envelope.entity
    payload = envelope.payload
    source = envelope.source
    extra = envelope.extra

    trial_event = {
        "stock_code": entity.get("stock_code", ""),
        "drug_name": payload.get("drug_name"),
        "trial_phase": payload.get("trial_phase"),
        "event_type": payload.get("event_type"),
        "event_date": payload.get("event_date"),
        "indication": payload.get("indication"),
        "summary_text": payload.get("summary_text"),
        "source_announcement_id": extra.get("source_announcement_id"),
        "source_type": source.get("source_type"),
        "source_url": source.get("source_url"),
    }

    req = IngestAnnouncementPackageRequest(
        clinical_trials=[trial_event]
    )

    return service_result_response(container.ingest.ingest_announcement_package(req))


def _ingest_regulatory_risk_event(envelope: OpenClawEnvelope, container: ServiceContainer):
    """监管风险事件入库"""
    from app.service.write_requests import IngestAnnouncementPackageRequest

    entity = envelope.entity
    payload = envelope.payload
    source = envelope.source
    extra = envelope.extra

    regulatory_risk = {
        "stock_code": entity.get("stock_code", ""),
        "risk_type": payload.get("risk_type"),
        "event_date": payload.get("event_date"),
        "risk_level": payload.get("risk_level"),
        "summary_text": payload.get("summary_text"),
        "source_announcement_id": extra.get("source_announcement_id"),
        "source_type": source.get("source_type"),
        "source_url": source.get("source_url"),
    }

    req = IngestAnnouncementPackageRequest(
        regulatory_risks=[regulatory_risk]
    )

    return service_result_response(container.ingest.ingest_announcement_package(req))


def _ingest_stock_daily(envelope: OpenClawEnvelope, container: ServiceContainer):
    """股票日行情入库"""
    from app.service.write_requests import IngestFinancialPackageRequest

    entity = envelope.entity
    payload = envelope.payload
    source = envelope.source

    stock_daily = {
        "stock_code": entity.get("stock_code", ""),
        "trade_date": payload.get("trade_date"),
        "open_price": payload.get("open_price"),
        "close_price": payload.get("close_price"),
        "high_price": payload.get("high_price"),
        "low_price": payload.get("low_price"),
        "volume": payload.get("volume"),
        "turnover": payload.get("turnover"),
        "source_type": source.get("source_type"),
    }

    req = IngestFinancialPackageRequest(
        stock_daily=[stock_daily]
    )

    return service_result_response(container.ingest.ingest_financial_package(req))


__all__ = ["router"]
