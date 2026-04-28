from __future__ import annotations

from hashlib import md5
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database.models.announcement_hot import (
    AnnouncementRawHot,
    AnnouncementStructuredHot,
    CentralizedProcurementEventHot,
    ClinicalTrialEventHot,
    DrugApprovalHot,
    RegulatoryRiskEventHot,
)
from app.core.database.models.company import CompanyMaster, CompanyProfile, IndustryMaster
from app.core.database.models.financial_hot import FinancialNotesHot
from app.core.database.models.research_report_hot import ResearchReportHot
from app.core.database.models.news_hot import (
    NewsCompanyMapHot,
    NewsIndustryMapHot,
    NewsRawHot,
    NewsStructuredHot,
)
from app.knowledge.store import ChunkMetadata, get_store, get_vector_store

try:
    from app.core.database.models.archive import (
        AnnouncementRawArchive,
        AnnouncementStructuredArchive,
        CentralizedProcurementEventArchive,
        ClinicalTrialEventArchive,
        DrugApprovalArchive,
        FinancialNotesArchive,
        NewsCompanyMapArchive,
        NewsIndustryMapArchive,
        NewsRawArchive,
        NewsStructuredArchive,
        RegulatoryRiskEventArchive,
    )
except Exception:
    AnnouncementRawArchive = None
    AnnouncementStructuredArchive = None
    DrugApprovalArchive = None
    ClinicalTrialEventArchive = None
    CentralizedProcurementEventArchive = None
    RegulatoryRiskEventArchive = None
    FinancialNotesArchive = None
    NewsRawArchive = None
    NewsStructuredArchive = None
    NewsIndustryMapArchive = None
    NewsCompanyMapArchive = None

try:
    from app.core.database.models.research_report_hot import ResearchReportArchive
except Exception:
    ResearchReportArchive = None


def _doc_id(prefix: str, pk: int, text: str) -> str:
    return f"{prefix}_{pk}_{md5((text or '')[:200].encode('utf-8')).hexdigest()[:10]}"


def _safe_attr(obj, name: str, default=""):
    return getattr(obj, name, default) if hasattr(obj, name) else default


def _normalize_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _delete_existing(doc_type: str, source_table: str, source_pk: int | str) -> None:
    try:
        get_vector_store().delete_by_source(
            doc_type=doc_type,
            source_table=source_table,
            source_pks=[str(source_pk)],
        )
    except Exception:
        pass
    try:
        get_store().delete_by_source(source_table=source_table, source_pks=[str(source_pk)])
    except Exception:
        pass


def _write_document(text: str, doc_type: str, meta: ChunkMetadata) -> int:
    meta_dict = meta.to_dict()
    _delete_existing(doc_type, meta.source_table, meta.source_pk)

    vec_count = get_vector_store().add_document(
        text=text,
        doc_type=doc_type,
        metadata=meta_dict,
        doc_id=meta.doc_id,
    )

    try:
        get_store().add_document(text, metadata=meta_dict)
    except Exception:
        pass

    return vec_count


def _first_scalar(db: Session, stmt):
    return db.execute(stmt).scalars().first()


def _choose_first_text(*values) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _stock_name_map(db: Session, stock_codes: Iterable[str]) -> dict[str, str]:
    codes = [c for c in {code for code in stock_codes if code}]
    if not codes:
        return {}
    try:
        rows = db.execute(
            select(CompanyMaster.stock_code, CompanyMaster.stock_name).where(CompanyMaster.stock_code.in_(codes))
        ).all()
        return {code: name or "" for code, name in rows}
    except Exception:
        return {}


def _load_announcement_metadata(db: Session, row, *, is_hot: bool) -> dict[str, str]:
    result = {
        "category": "",
        "signal_type": "",
        "risk_level": "",
        "drug_name": "",
        "indication": "",
        "trial_phase": "",
        "event_type": "",
    }

    StructuredModel = AnnouncementStructuredHot if is_hot else AnnouncementStructuredArchive
    DrugModel = DrugApprovalHot if is_hot else DrugApprovalArchive
    TrialModel = ClinicalTrialEventHot if is_hot else ClinicalTrialEventArchive
    ProcurementModel = CentralizedProcurementEventHot if is_hot else CentralizedProcurementEventArchive
    RiskModel = RegulatoryRiskEventHot if is_hot else RegulatoryRiskEventArchive

    if StructuredModel is not None:
        try:
            structured = _first_scalar(db, select(StructuredModel).where(StructuredModel.announcement_id == row.id))
            if structured:
                result["category"] = _choose_first_text(_safe_attr(structured, "category"))
                result["signal_type"] = _choose_first_text(_safe_attr(structured, "signal_type"))
                result["risk_level"] = _choose_first_text(_safe_attr(structured, "risk_level"))
        except Exception:
            pass

    if DrugModel is not None:
        try:
            drug = _first_scalar(db, select(DrugModel).where(DrugModel.source_announcement_id == row.id))
            if drug:
                result["drug_name"] = _choose_first_text(_safe_attr(drug, "drug_name"))
                result["indication"] = _choose_first_text(_safe_attr(drug, "indication"))
                result["event_type"] = _choose_first_text(_safe_attr(drug, "approval_type"), "drug_approval")
        except Exception:
            pass

    if TrialModel is not None:
        try:
            trial = _first_scalar(db, select(TrialModel).where(TrialModel.source_announcement_id == row.id))
            if trial:
                result["drug_name"] = _choose_first_text(result["drug_name"], _safe_attr(trial, "drug_name"))
                result["indication"] = _choose_first_text(result["indication"], _safe_attr(trial, "indication"))
                result["trial_phase"] = _choose_first_text(_safe_attr(trial, "trial_phase"))
                result["event_type"] = _choose_first_text(result["event_type"], _safe_attr(trial, "event_type"), "clinical_trial")
        except Exception:
            pass

    if ProcurementModel is not None:
        try:
            procurement = _first_scalar(db, select(ProcurementModel).where(ProcurementModel.source_announcement_id == row.id))
            if procurement:
                result["drug_name"] = _choose_first_text(result["drug_name"], _safe_attr(procurement, "drug_name"))
                result["event_type"] = _choose_first_text(result["event_type"], "centralized_procurement")
                result["category"] = _choose_first_text(result["category"], "centralized_procurement")
        except Exception:
            pass

    if RiskModel is not None:
        try:
            risk = _first_scalar(db, select(RiskModel).where(RiskModel.source_announcement_id == row.id))
            if risk:
                result["risk_level"] = _choose_first_text(result["risk_level"], _safe_attr(risk, "risk_level"))
                result["event_type"] = _choose_first_text(result["event_type"], _safe_attr(risk, "risk_type"), "regulatory_risk")
                result["category"] = _choose_first_text(result["category"], "regulatory_risk")
        except Exception:
            pass

    return result


def sync_announcements(
    db: Session,
    is_hot: bool = True,
    stock_code: str | None = None,
    limit: int | None = None,
) -> int:
    Model = AnnouncementRawHot if is_hot else AnnouncementRawArchive
    if Model is None:
        return 0

    stmt = select(Model)
    if stock_code:
        stmt = stmt.where(Model.stock_code == stock_code)
    if limit:
        stmt = stmt.limit(limit)

    rows = db.execute(stmt).scalars().all()
    stock_name_by_code = _stock_name_map(db, [getattr(r, "stock_code", "") for r in rows])

    total = 0
    for row in rows:
        content = _normalize_text(_safe_attr(row, "content")) or _normalize_text(_safe_attr(row, "summary_text"))
        if not content:
            continue

        extra = _load_announcement_metadata(db, row, is_hot=is_hot)
        meta = ChunkMetadata(
            doc_type="announcement",
            doc_id=_doc_id("announcement", row.id, content),
            stock_code=_safe_attr(row, "stock_code", "") or "",
            stock_name=stock_name_by_code.get(_safe_attr(row, "stock_code", "") or "", ""),
            title=_safe_attr(row, "title", "") or "",
            publish_date=str(_safe_attr(row, "publish_date", "") or ""),
            category=extra["category"],
            signal_type=extra["signal_type"],
            risk_level=extra["risk_level"],
            drug_name=extra["drug_name"],
            indication=extra["indication"],
            trial_phase=extra["trial_phase"],
            event_type=extra["event_type"],
            source_type=_safe_attr(row, "source_type", "") or "",
            source_url=_safe_attr(row, "source_url", "") or "",
            source_table=Model.__tablename__,
            source_pk=str(row.id),
            is_hot=1 if is_hot else 0,
        )
        total += _write_document(content, "announcement", meta)

    return total


def sync_announcements_by_ids(db: Session, source_ids: list[int], is_hot: bool = True) -> int:
    Model = AnnouncementRawHot if is_hot else AnnouncementRawArchive
    if Model is None or not source_ids:
        return 0
    stmt = select(Model).where(Model.id.in_(source_ids))
    rows = db.execute(stmt).scalars().all()
    stock_name_by_code = _stock_name_map(db, [getattr(r, "stock_code", "") for r in rows])

    total = 0
    for row in rows:
        content = _normalize_text(_safe_attr(row, "content"))
        if not content:
            continue
        extra = _load_announcement_metadata(db, row, is_hot=is_hot)
        meta = ChunkMetadata(
            doc_type="announcement",
            doc_id=_doc_id("announcement", row.id, content),
            stock_code=_safe_attr(row, "stock_code", "") or "",
            stock_name=stock_name_by_code.get(_safe_attr(row, "stock_code", "") or "", ""),
            title=_safe_attr(row, "title", "") or "",
            publish_date=str(_safe_attr(row, "publish_date", "") or ""),
            category=extra["category"],
            signal_type=extra["signal_type"],
            risk_level=extra["risk_level"],
            drug_name=extra["drug_name"],
            indication=extra["indication"],
            trial_phase=extra["trial_phase"],
            event_type=extra["event_type"],
            source_type=_safe_attr(row, "source_type", "") or "",
            source_url=_safe_attr(row, "source_url", "") or "",
            source_table=Model.__tablename__,
            source_pk=str(row.id),
            is_hot=1 if is_hot else 0,
        )
        total += _write_document(content, "announcement", meta)
    return total


def sync_financial_notes(
    db: Session,
    is_hot: bool = True,
    stock_code: str | None = None,
    limit: int | None = None,
) -> int:
    Model = FinancialNotesHot if is_hot else FinancialNotesArchive
    if Model is None:
        return 0

    stmt = select(Model)
    if stock_code:
        stmt = stmt.where(Model.stock_code == stock_code)
    if limit:
        stmt = stmt.limit(limit)

    rows = db.execute(stmt).scalars().all()
    stock_name_by_code = _stock_name_map(db, [getattr(r, "stock_code", "") for r in rows])

    total = 0
    for row in rows:
        text_value = _normalize_text(_safe_attr(row, "note_text"))
        if not text_value:
            continue

        meta = ChunkMetadata(
            doc_type="financial_note",
            doc_id=_doc_id("financial_note", row.id, text_value),
            stock_code=_safe_attr(row, "stock_code", "") or "",
            stock_name=stock_name_by_code.get(_safe_attr(row, "stock_code", "") or "", ""),
            publish_date=str(_safe_attr(row, "report_date", "") or ""),
            category=_safe_attr(row, "note_type", "") or "",
            source_type=_safe_attr(row, "source_type", "") or "",
            source_url=_safe_attr(row, "source_url", "") or "",
            source_table=Model.__tablename__,
            source_pk=str(row.id),
            is_hot=1 if is_hot else 0,
        )
        total += _write_document(text_value, "financial_note", meta)

    return total


def sync_financial_notes_by_ids(db: Session, source_ids: list[int], is_hot: bool = True) -> int:
    Model = FinancialNotesHot if is_hot else FinancialNotesArchive
    if Model is None or not source_ids:
        return 0

    stmt = select(Model).where(Model.id.in_(source_ids))
    rows = db.execute(stmt).scalars().all()
    stock_name_by_code = _stock_name_map(db, [getattr(r, "stock_code", "") for r in rows])

    total = 0
    for row in rows:
        text_value = _normalize_text(_safe_attr(row, "note_text"))
        if not text_value:
            continue
        meta = ChunkMetadata(
            doc_type="financial_note",
            doc_id=_doc_id("financial_note", row.id, text_value),
            stock_code=_safe_attr(row, "stock_code", "") or "",
            stock_name=stock_name_by_code.get(_safe_attr(row, "stock_code", "") or "", ""),
            publish_date=str(_safe_attr(row, "report_date", "") or ""),
            category=_safe_attr(row, "note_type", "") or "",
            source_type=_safe_attr(row, "source_type", "") or "",
            source_url=_safe_attr(row, "source_url", "") or "",
            source_table=Model.__tablename__,
            source_pk=str(row.id),
            is_hot=1 if is_hot else 0,
        )
        total += _write_document(text_value, "financial_note", meta)
    return total


def sync_company_profiles(db: Session, stock_code: str | None = None, limit: int | None = None) -> int:
    stmt = select(CompanyProfile, CompanyMaster.stock_name).join(CompanyMaster, CompanyProfile.stock_code == CompanyMaster.stock_code)
    if stock_code:
        stmt = stmt.where(CompanyProfile.stock_code == stock_code)
    if limit:
        stmt = stmt.limit(limit)

    rows = db.execute(stmt).all()
    total = 0
    for profile, stock_name in rows:
        parts = [p for p in [profile.business_summary, profile.market_position, profile.management_summary] if p]
        if not parts:
            continue

        text = "\n".join(parts)
        meta = ChunkMetadata(
            doc_type="company_profile",
            doc_id=_doc_id("company_profile", profile.id, text),
            stock_code=profile.stock_code or "",
            stock_name=stock_name or "",
            title=stock_name or "",
            source_table=CompanyProfile.__tablename__,
            source_pk=str(profile.id),
            is_hot=1,
        )
        total += _write_document(text, "company_profile", meta)

    return total


def sync_company_profiles_by_ids(db: Session, source_ids: list[int]) -> int:
    if not source_ids:
        return 0

    stmt = (
        select(CompanyProfile, CompanyMaster.stock_name)
        .join(CompanyMaster, CompanyProfile.stock_code == CompanyMaster.stock_code)
        .where(CompanyProfile.id.in_(source_ids))
    )
    rows = db.execute(stmt).all()

    total = 0
    for profile, stock_name in rows:
        parts = [p for p in [profile.business_summary, profile.market_position, profile.management_summary] if p]
        if not parts:
            continue

        text = "\n".join(parts)
        meta = ChunkMetadata(
            doc_type="company_profile",
            doc_id=_doc_id("company_profile", profile.id, text),
            stock_code=profile.stock_code or "",
            stock_name=stock_name or "",
            title=stock_name or "",
            source_table=CompanyProfile.__tablename__,
            source_pk=str(profile.id),
            is_hot=1,
        )
        total += _write_document(text, "company_profile", meta)
    return total


def _load_news_related_metadata(db: Session, row, *, is_hot: bool) -> dict[str, str]:
    result = {
        "topic_category": "",
        "signal_type": "",
        "impact_level": "",
        "impact_horizon": "",
        "industry_code": "",
        "industry_name": "",
        "stock_code": "",
        "impact_direction": "",
    }

    StructuredModel = NewsStructuredHot if is_hot else NewsStructuredArchive
    IndustryMapModel = NewsIndustryMapHot if is_hot else NewsIndustryMapArchive
    CompanyMapModel = NewsCompanyMapHot if is_hot else NewsCompanyMapArchive

    if StructuredModel is not None:
        try:
            structured = _first_scalar(db, select(StructuredModel).where(StructuredModel.news_id == row.id))
            if structured:
                result["topic_category"] = _choose_first_text(_safe_attr(structured, "topic_category"))
                result["signal_type"] = _choose_first_text(_safe_attr(structured, "signal_type"))
                result["impact_level"] = _choose_first_text(_safe_attr(structured, "impact_level"))
                result["impact_horizon"] = _choose_first_text(_safe_attr(structured, "impact_horizon"))
        except Exception:
            pass

    if CompanyMapModel is not None:
        try:
            company_map = _first_scalar(db, select(CompanyMapModel).where(CompanyMapModel.news_id == row.id))
            if company_map:
                result["stock_code"] = _choose_first_text(_safe_attr(company_map, "stock_code"))
                result["impact_direction"] = _choose_first_text(_safe_attr(company_map, "impact_direction"))
        except Exception:
            pass

    if IndustryMapModel is not None:
        try:
            industry_map = _first_scalar(db, select(IndustryMapModel).where(IndustryMapModel.news_id == row.id))
            if industry_map:
                result["industry_code"] = _choose_first_text(_safe_attr(industry_map, "industry_code"))
                result["impact_direction"] = _choose_first_text(result["impact_direction"], _safe_attr(industry_map, "impact_direction"))
                if result["industry_code"]:
                    try:
                        industry_name = db.execute(
                            select(IndustryMaster.industry_name).where(IndustryMaster.industry_code == result["industry_code"])
                        ).scalar_one_or_none()
                        result["industry_name"] = industry_name or ""
                    except Exception:
                        pass
        except Exception:
            pass

    return result


def sync_news(db: Session, is_hot: bool = True, stock_code: str | None = None, limit: int | None = None) -> int:
    RawModel = NewsRawHot if is_hot else NewsRawArchive
    CompanyMapModel = NewsCompanyMapHot if is_hot else NewsCompanyMapArchive
    if RawModel is None:
        return 0

    stmt = select(RawModel)
    if stock_code and CompanyMapModel is not None:
        stmt = stmt.join(CompanyMapModel, CompanyMapModel.news_id == RawModel.id).where(CompanyMapModel.stock_code == stock_code)
    if limit:
        stmt = stmt.limit(limit)

    rows = db.execute(stmt).scalars().all()
    total = 0
    stock_name_by_code: dict[str, str] = {}
    for row in rows:
        content = _normalize_text(_safe_attr(row, "content"))
        if not content:
            continue

        extra = _load_news_related_metadata(db, row, is_hot=is_hot)
        stock_code_m = _choose_first_text(stock_code, extra["stock_code"])
        if stock_code_m and stock_code_m not in stock_name_by_code:
            stock_name_by_code.update(_stock_name_map(db, [stock_code_m]))

        publish_time = _safe_attr(row, "publish_time", None)
        publish_date = str(publish_time.date()) if publish_time else ""

        meta = ChunkMetadata(
            doc_type="news",
            doc_id=_doc_id("news", row.id, content),
            stock_code=stock_code_m,
            stock_name=stock_name_by_code.get(stock_code_m, ""),
            title=_safe_attr(row, "title", "") or "",
            publish_date=publish_date,
            category=extra["topic_category"],
            topic_category=extra["topic_category"],
            signal_type=extra["signal_type"],
            impact_level=extra["impact_level"],
            impact_direction=extra["impact_direction"],
            impact_horizon=extra["impact_horizon"],
            source_type=_safe_attr(row, "source_name", "") or _safe_attr(row, "source_type", "") or "",
            source_url=_safe_attr(row, "source_url", "") or "",
            source_table=RawModel.__tablename__,
            source_pk=str(row.id),
            industry_code=extra["industry_code"],
            industry_name=extra["industry_name"],
            is_hot=1 if is_hot else 0,
        )
        total += _write_document(content, "news", meta)

    return total


def sync_news_by_ids(db: Session, source_ids: list[int], is_hot: bool = True) -> int:
    RawModel = NewsRawHot if is_hot else NewsRawArchive
    if RawModel is None or not source_ids:
        return 0

    stmt = select(RawModel).where(RawModel.id.in_(source_ids))
    rows = db.execute(stmt).scalars().all()

    total = 0
    stock_name_by_code: dict[str, str] = {}
    for row in rows:
        content = _normalize_text(_safe_attr(row, "content"))
        if not content:
            continue

        extra = _load_news_related_metadata(db, row, is_hot=is_hot)
        stock_code_m = extra["stock_code"]
        if stock_code_m and stock_code_m not in stock_name_by_code:
            stock_name_by_code.update(_stock_name_map(db, [stock_code_m]))

        publish_time = _safe_attr(row, "publish_time", None)
        publish_date = str(publish_time.date()) if publish_time else ""

        meta = ChunkMetadata(
            doc_type="news",
            doc_id=_doc_id("news", row.id, content),
            stock_code=stock_code_m,
            stock_name=stock_name_by_code.get(stock_code_m, ""),
            title=_safe_attr(row, "title", "") or "",
            publish_date=publish_date,
            category=extra["topic_category"],
            topic_category=extra["topic_category"],
            signal_type=extra["signal_type"],
            impact_level=extra["impact_level"],
            impact_direction=extra["impact_direction"],
            impact_horizon=extra["impact_horizon"],
            source_type=_safe_attr(row, "source_name", "") or _safe_attr(row, "source_type", "") or "",
            source_url=_safe_attr(row, "source_url", "") or "",
            source_table=RawModel.__tablename__,
            source_pk=str(row.id),
            industry_code=extra["industry_code"],
            industry_name=extra["industry_name"],
            is_hot=1 if is_hot else 0,
        )
        total += _write_document(content, "news", meta)
    return total


def sync_external_document(
    *,
    text: str,
    doc_type: str,
    source_pk: str,
    title: str = "",
    stock_code: str = "",
    stock_name: str = "",
    publish_date: str = "",
    category: str = "",
    source_type: str = "external",
    source_url: str = "",
    industry_code: str = "",
    industry_name: str = "",
    is_hot: int = 1,
) -> int:
    text = _normalize_text(text)
    if not text:
        return 0
    meta = ChunkMetadata(
        doc_type=doc_type,
        doc_id=f"{doc_type}_{md5(str(source_pk).encode('utf-8')).hexdigest()[:12]}",
        stock_code=stock_code,
        stock_name=stock_name,
        title=title,
        publish_date=publish_date,
        category=category,
        source_type=source_type,
        source_url=source_url,
        source_table=f"external_{doc_type}",
        source_pk=str(source_pk),
        industry_code=industry_code,
        industry_name=industry_name,
        is_hot=is_hot,
    )
    return _write_document(text, doc_type, meta)


def _resolve_industry_name(db: Session, industry_code: str) -> str:
    if not industry_code:
        return ""
    try:
        name = db.execute(
            select(IndustryMaster.industry_name).where(IndustryMaster.industry_code == industry_code)
        ).scalar_one_or_none()
        return name or ""
    except Exception:
        return ""


def _sync_research_report_row(db: Session, row, *, is_hot: bool, stock_name_by_code: dict[str, str]) -> int:
    content = _normalize_text(_safe_attr(row, "content")) or _normalize_text(_safe_attr(row, "summary_text"))
    if not content:
        return 0

    stock_code = _safe_attr(row, "stock_code", "") or ""
    industry_code = _safe_attr(row, "industry_code", "") or ""
    industry_name = _resolve_industry_name(db, industry_code) if industry_code else ""
    source_table = ResearchReportHot.__tablename__ if is_hot else (ResearchReportArchive.__tablename__ if ResearchReportArchive else "research_report_archive")

    meta = ChunkMetadata(
        doc_type="report",
        doc_id=_doc_id("report", row.id, content),
        stock_code=stock_code,
        stock_name=stock_name_by_code.get(stock_code, ""),
        title=_safe_attr(row, "title", "") or "",
        publish_date=str(_safe_attr(row, "publish_date", "") or ""),
        category=_safe_attr(row, "scope_type", "") or "",
        source_type=_safe_attr(row, "source_type", "") or "",
        source_url=_safe_attr(row, "source_url", "") or "",
        source_table=source_table,
        source_pk=str(row.id),
        industry_code=industry_code,
        industry_name=industry_name,
        is_hot=1 if is_hot else 0,
    )
    return _write_document(content, "report", meta)


def sync_research_reports(
    db: Session,
    is_hot: bool = True,
    stock_code: str | None = None,
    limit: int | None = None,
) -> int:
    Model = ResearchReportHot if is_hot else ResearchReportArchive
    if Model is None:
        return 0

    stmt = select(Model)
    if stock_code:
        stmt = stmt.where(Model.stock_code == stock_code)
    if limit:
        stmt = stmt.limit(limit)

    rows = db.execute(stmt).scalars().all()
    stock_name_by_code = _stock_name_map(db, [getattr(r, "stock_code", "") for r in rows])

    total = 0
    for row in rows:
        total += _sync_research_report_row(db, row, is_hot=is_hot, stock_name_by_code=stock_name_by_code)
    return total


def sync_research_reports_by_ids(db: Session, source_ids: list[int], is_hot: bool = True) -> int:
    Model = ResearchReportHot if is_hot else ResearchReportArchive
    if Model is None or not source_ids:
        return 0

    stmt = select(Model).where(Model.id.in_(source_ids))
    rows = db.execute(stmt).scalars().all()
    stock_name_by_code = _stock_name_map(db, [getattr(r, "stock_code", "") for r in rows])

    total = 0
    for row in rows:
        total += _sync_research_report_row(db, row, is_hot=is_hot, stock_name_by_code=stock_name_by_code)
    return total
