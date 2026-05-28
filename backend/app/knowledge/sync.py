from __future__ import annotations

import os
from datetime import date, datetime
from hashlib import sha256
from hashlib import md5
from typing import Iterable

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.core.database.models.announcement_hot import (
    AnnouncementRawArchive,
    AnnouncementRawHot,
    AnnouncementStructuredArchive,
    AnnouncementStructuredHot,
    CentralizedProcurementEventArchive,
    CentralizedProcurementEventHot,
    ClinicalTrialEventArchive,
    ClinicalTrialEventHot,
    DrugApprovalArchive,
    DrugApprovalHot,
    RegulatoryRiskEventArchive,
    RegulatoryRiskEventHot,
)
from app.core.database.models.company import CompanyMaster, CompanyProfile, IndustryMaster
from app.core.database.models.financial_hot import FinancialNotesArchive, FinancialNotesHot
from app.core.database.models.research_report_hot import ResearchReportArchive, ResearchReportHot
from app.core.database.models.news_hot import (
    NewsCompanyMapArchive,
    NewsCompanyMapHot,
    NewsIndustryMapArchive,
    NewsIndustryMapHot,
    NewsRawArchive,
    NewsRawHot,
    NewsStructuredArchive,
    NewsStructuredHot,
)
from app.core.database.models.pipeline import PipelineDrug
from app.core.database.models.vector_and_job import VectorDocumentIndex
from app.knowledge.store import (
    ACTIVE_COLLECTIONS,
    EMBEDDING_MODEL_NAME,
    ChunkMetadata,
    build_chunk_payloads,
    get_store,
    get_vector_store,
)

_TRUTHY = {"1", "true", "yes", "on"}


def _tfidf_fallback_write_enabled() -> bool:
    return os.getenv("ENABLE_TFIDF_FALLBACK_WRITE", "").strip().lower() in _TRUTHY


def _doc_id(prefix: str, pk: int | str, text: str) -> str:
    return f"{prefix}_{pk}_{md5((text or '')[:200].encode('utf-8')).hexdigest()[:10]}"


def _safe_attr(obj, name: str, default=""):
    return getattr(obj, name, default) if hasattr(obj, name) else default


def _normalize_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _source_uid(row, fallback_prefix: str) -> str:
    for attr in ("dedup_key", "announcement_uid", "report_uid", "news_uid"):
        value = _normalize_text(_safe_attr(row, attr, ""))
        if value:
            return value
    return f"{fallback_prefix}:{_safe_attr(row, 'id', '')}"


def _source_id_for_index(source_pk: int | str, source_uid: str = "") -> int:
    text = str(source_pk or "").strip()
    try:
        return int(text)
    except (TypeError, ValueError):
        seed = source_uid or text
        return int(sha256(seed.encode("utf-8")).hexdigest()[:15], 16)


def _parse_publish_time(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        try:
            return datetime.fromisoformat(text[:10])
        except ValueError:
            return None


def delete_vector_index_entries(
    db: Session,
    *,
    source_table: str,
    source_pks: list[int | str],
    source_uids: list[str] | None = None,
) -> int:
    conditions = []
    source_uids = [str(uid) for uid in (source_uids or []) if uid]
    for source_uid in source_uids:
        conditions.append(VectorDocumentIndex.source_uid == source_uid)
    for source_pk in source_pks:
        conditions.append(
            (VectorDocumentIndex.source_table == source_table)
            & (VectorDocumentIndex.source_id == _source_id_for_index(source_pk))
        )
    if not conditions:
        return 0
    result = db.execute(delete(VectorDocumentIndex).where(or_(*conditions)))
    return int(result.rowcount or 0)


def _set_source_vector_status(row, status: str) -> None:
    if row is not None and hasattr(row, "vector_status"):
        try:
            setattr(row, "vector_status", status)
        except Exception:
            pass


def _write_vector_index_entries(
    db: Session,
    *,
    meta: ChunkMetadata,
    chunks: list[dict],
    vector_status: str,
) -> int:
    if not chunks:
        return 0

    source_id = _source_id_for_index(meta.source_pk, meta.source_uid)
    publish_time = _parse_publish_time(meta.publish_date)
    if vector_status == "success":
        vector_collection = ACTIVE_COLLECTIONS.get(meta.doc_type)
    elif vector_status == "fallback_only":
        vector_collection = "tfidf_fallback"
    else:
        vector_collection = None

    rows = []
    for chunk in chunks:
        vector_id = None
        if vector_status == "success":
            vector_id = chunk["id"]
        elif vector_status == "fallback_only":
            vector_id = f"tfidf:{chunk['id']}"
        rows.append(
            VectorDocumentIndex(
                doc_type=meta.doc_type,
                source_table=meta.source_table,
                source_id=source_id,
                source_uid=meta.source_uid or None,
                stock_code=meta.stock_code or None,
                industry_code=meta.industry_code or None,
                title=meta.title or None,
                publish_time=publish_time,
                chunk_index=int(chunk["chunk_index"]),
                chunk_text=chunk["text"],
                vector_collection=vector_collection,
                vector_id=vector_id,
                embedding_model=EMBEDDING_MODEL_NAME,
                vector_status=vector_status,
            )
        )
    db.add_all(rows)
    db.flush()
    return len(rows)


def _financial_note_text(row) -> str:
    note_text = _normalize_text(_safe_attr(row, "note_text"))
    if note_text:
        return note_text

    report_type = _normalize_text(_safe_attr(row, "report_type"))
    if report_type == "daily":
        return ""

    fields = [
        ("stock_code", "股票代码"),
        ("report_date", "报告日期"),
        ("fiscal_year", "会计年度"),
        ("report_type", "报告类型"),
        ("revenue", "营业收入"),
        ("operating_cost", "营业成本"),
        ("gross_profit", "毛利润"),
        ("gross_margin", "毛利率"),
        ("selling_expense", "销售费用"),
        ("admin_expense", "管理费用"),
        ("rd_expense", "研发费用"),
        ("rd_ratio", "研发费用率"),
        ("operating_profit", "营业利润"),
        ("net_profit", "净利润"),
        ("net_profit_deducted", "扣非净利润"),
        ("eps", "每股收益"),
        ("total_assets", "总资产"),
        ("total_liabilities", "总负债"),
        ("debt_ratio", "资产负债率"),
        ("operating_cashflow", "经营现金流"),
        ("source_url", "来源"),
    ]
    parts = []
    for attr, label in fields:
        value = _normalize_text(_safe_attr(row, attr))
        if value:
            parts.append(f"{label}: {value}")
    return "；".join(parts)


def _delete_existing_stores(doc_type: str, source_table: str, source_pk: int | str, source_uid: str = "") -> None:
    try:
        get_vector_store().delete_by_source(
            doc_type=doc_type,
            source_table=source_table,
            source_pks=[str(source_pk)],
            source_uids=[source_uid] if source_uid else None,
        )
    except Exception:
        pass
    if _tfidf_fallback_write_enabled():
        try:
            get_store().delete_by_source(
                source_table=source_table,
                source_pks=[str(source_pk)],
                source_uids=[source_uid] if source_uid else None,
            )
        except Exception:
            pass


def _delete_existing(db: Session, doc_type: str, source_table: str, source_pk: int | str, source_uid: str = "") -> None:
    _delete_existing_stores(doc_type, source_table, source_pk, source_uid)
    try:
        delete_vector_index_entries(
            db,
            source_table=source_table,
            source_pks=[source_pk],
            source_uids=[source_uid] if source_uid else None,
        )
    except Exception:
        pass


def _write_document_without_index(text: str, doc_type: str, meta: ChunkMetadata) -> int:
    meta_dict = meta.to_dict()
    chunks = build_chunk_payloads(text, doc_type, meta_dict, meta.doc_id)
    _delete_existing_stores(doc_type, meta.source_table, meta.source_pk, meta.source_uid)
    if not chunks:
        return 0

    vec_count = get_vector_store().add_document(
        text=text,
        doc_type=doc_type,
        metadata=meta_dict,
        doc_id=meta.doc_id,
    )
    if _tfidf_fallback_write_enabled():
        try:
            get_store().add_document(text, metadata=meta_dict)
        except Exception:
            pass
    return vec_count


def _write_document(db: Session, text: str, doc_type: str, meta: ChunkMetadata, source_row=None) -> int:
    meta_dict = meta.to_dict()
    chunks = build_chunk_payloads(text, doc_type, meta_dict, meta.doc_id)
    _delete_existing(db, doc_type, meta.source_table, meta.source_pk, meta.source_uid)
    if not chunks:
        _set_source_vector_status(source_row, "skipped_empty")
        return 0

    vec_count = get_vector_store().add_document(
        text=text,
        doc_type=doc_type,
        metadata=meta_dict,
        doc_id=meta.doc_id,
    )

    tfidf_ok = False
    if _tfidf_fallback_write_enabled():
        try:
            get_store().add_document(text, metadata=meta_dict)
            tfidf_ok = True
        except Exception:
            pass

    if vec_count > 0:
        vector_status = "success"
    elif tfidf_ok:
        vector_status = "fallback_only"
    else:
        vector_status = "failed"
    _write_vector_index_entries(db, meta=meta, chunks=chunks, vector_status=vector_status)
    _set_source_vector_status(source_row, vector_status)

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
            source_uid=_source_uid(row, "announcement"),
            is_hot=1 if is_hot else 0,
        )
        total += _write_document(db, content, "announcement", meta, row)

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
            source_uid=_source_uid(row, "announcement"),
            is_hot=1 if is_hot else 0,
        )
        total += _write_document(db, content, "announcement", meta, row)
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
        text_value = _financial_note_text(row)
        if not text_value:
            continue

        meta = ChunkMetadata(
            doc_type="financial_note",
            doc_id=_doc_id("financial_note", row.id, text_value),
            stock_code=_safe_attr(row, "stock_code", "") or "",
            stock_name=stock_name_by_code.get(_safe_attr(row, "stock_code", "") or "", ""),
            publish_date=str(_safe_attr(row, "report_date", "") or ""),
            category=_safe_attr(row, "note_type", "") or _safe_attr(row, "report_type", "") or "",
            source_type=_safe_attr(row, "source_type", "") or "",
            source_url=_safe_attr(row, "source_url", "") or "",
            source_table=Model.__tablename__,
            source_pk=str(row.id),
            source_uid=_source_uid(row, "financial"),
            is_hot=1 if is_hot else 0,
        )
        total += _write_document(db, text_value, "financial_note", meta, row)

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
        text_value = _financial_note_text(row)
        if not text_value:
            continue
        meta = ChunkMetadata(
            doc_type="financial_note",
            doc_id=_doc_id("financial_note", row.id, text_value),
            stock_code=_safe_attr(row, "stock_code", "") or "",
            stock_name=stock_name_by_code.get(_safe_attr(row, "stock_code", "") or "", ""),
            publish_date=str(_safe_attr(row, "report_date", "") or ""),
            category=_safe_attr(row, "note_type", "") or _safe_attr(row, "report_type", "") or "",
            source_type=_safe_attr(row, "source_type", "") or "",
            source_url=_safe_attr(row, "source_url", "") or "",
            source_table=Model.__tablename__,
            source_pk=str(row.id),
            source_uid=_source_uid(row, "financial"),
            is_hot=1 if is_hot else 0,
        )
        total += _write_document(db, text_value, "financial_note", meta, row)
    return total


def sync_company_profiles(db: Session, stock_code: str | None = None, limit: int | None = None) -> int:
    stmt = select(CompanyProfile)
    if stock_code:
        stmt = stmt.where(CompanyProfile.stock_code == stock_code)
    if limit:
        stmt = stmt.limit(limit)

    rows = db.execute(stmt).scalars().all()
    total = 0
    for profile in rows:
        stock_name = getattr(profile, "stock_name", "") or ""
        parts = [p for p in [profile.business_summary, profile.market_position, profile.management_summary] if p]
        if not parts:
            continue

        text = "\n".join(parts)
        meta = ChunkMetadata(
            doc_type="company_profile",
            doc_id=_doc_id("company_profile", profile.stock_code, text),
            stock_code=profile.stock_code or "",
            stock_name=stock_name,
            title=stock_name,
            source_table=CompanyProfile.__tablename__,
            source_pk=profile.stock_code or "",
            source_uid=f"company:{profile.stock_code}",
            is_hot=1,
        )
        total += _write_document(db, text, "company_profile", meta, profile)

    return total


def sync_company_profiles_by_ids(db: Session, source_ids: list[int | str]) -> int:
    if not source_ids:
        return 0

    stmt = (
        select(CompanyProfile)
        .where(CompanyProfile.stock_code.in_([str(s) for s in source_ids]))
    )
    rows = db.execute(stmt).scalars().all()

    total = 0
    for profile in rows:
        stock_name = getattr(profile, "stock_name", "") or ""
        parts = [p for p in [profile.business_summary, profile.market_position, profile.management_summary] if p]
        if not parts:
            continue

        text = "\n".join(parts)
        meta = ChunkMetadata(
            doc_type="company_profile",
            doc_id=_doc_id("company_profile", profile.stock_code, text),
            stock_code=profile.stock_code or "",
            stock_name=stock_name,
            title=stock_name,
            source_table=CompanyProfile.__tablename__,
            source_pk=profile.stock_code or "",
            source_uid=f"company:{profile.stock_code}",
            is_hot=1,
        )
        total += _write_document(db, text, "company_profile", meta, profile)
    return total


def _load_news_related_metadata(db: Session, row, *, is_hot: bool) -> dict[str, str]:
    """从 NewsHot/NewsArchive 自身字段提取关联元数据（v3 合表后不再 join 扩展表）。"""
    import json as _json

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

    # news_type 即 topic_category
    result["topic_category"] = _choose_first_text(_safe_attr(row, "news_type"))

    # key_fields_json 包含结构化字段
    kf = getattr(row, "key_fields_json", None) or {}
    if isinstance(kf, str):
        try:
            kf = _json.loads(kf)
        except Exception:
            kf = {}
    if isinstance(kf, dict):
        result["signal_type"] = _choose_first_text(kf.get("signal_type", ""))
        result["impact_level"] = _choose_first_text(kf.get("impact_level", ""))
        result["impact_horizon"] = _choose_first_text(kf.get("impact_horizon", ""))
        result["impact_direction"] = _choose_first_text(kf.get("impact_direction", ""))

    # related_stock_codes_json 取第一个 stock_code
    stock_codes = getattr(row, "related_stock_codes_json", None)
    if isinstance(stock_codes, str):
        try:
            stock_codes = _json.loads(stock_codes)
        except Exception:
            stock_codes = None
    if isinstance(stock_codes, list) and stock_codes:
        result["stock_code"] = str(stock_codes[0])
    elif isinstance(stock_codes, dict) and stock_codes:
        result["stock_code"] = str(next(iter(stock_codes.values()), ""))

    # related_industry_codes_json 取第一个 industry_code
    industry_codes = getattr(row, "related_industry_codes_json", None)
    if isinstance(industry_codes, str):
        try:
            industry_codes = _json.loads(industry_codes)
        except Exception:
            industry_codes = None
    if isinstance(industry_codes, list) and industry_codes:
        result["industry_code"] = str(industry_codes[0])
    elif isinstance(industry_codes, dict) and industry_codes:
        result["industry_code"] = str(next(iter(industry_codes.values()), ""))

    if result["industry_code"]:
        try:
            industry_name = db.execute(
                select(IndustryMaster.industry_name).where(IndustryMaster.industry_code == result["industry_code"])
            ).scalar_one_or_none()
            result["industry_name"] = industry_name or ""
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
            source_uid=_source_uid(row, "news"),
            industry_code=extra["industry_code"],
            industry_name=extra["industry_name"],
            is_hot=1 if is_hot else 0,
        )
        total += _write_document(db, content, "news", meta, row)

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
            source_uid=_source_uid(row, "news"),
            industry_code=extra["industry_code"],
            industry_name=extra["industry_name"],
            is_hot=1 if is_hot else 0,
        )
        total += _write_document(db, content, "news", meta, row)
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
        source_uid=f"external:{doc_type}:{source_pk}",
        industry_code=industry_code,
        industry_name=industry_name,
        is_hot=is_hot,
    )
    from app.core.database.session import SessionLocal

    try:
        with SessionLocal() as db:
            try:
                count = _write_document(db, text, doc_type, meta)
                db.commit()
                return count
            except Exception:
                db.rollback()
                raise
    except Exception:
        return _write_document_without_index(text, doc_type, meta)


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
        source_uid=_source_uid(row, "research_report"),
        industry_code=industry_code,
        industry_name=industry_name,
        is_hot=1 if is_hot else 0,
    )
    return _write_document(db, content, "report", meta, row)


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


def _pipeline_drug_text(row) -> str:
    parts = []
    if row.stock_code:
        parts.append(f"公司：{row.stock_code}")
    parts.append(f"药品：{row.drug_name}")
    if row.indication:
        parts.append(f"适应症：{row.indication}")
    if row.therapeutic_area:
        parts.append(f"治疗领域：{row.therapeutic_area}")
    parts.append(f"阶段：{row.trial_phase}")
    if row.trial_phase_raw:
        parts.append(f"原始表述：{row.trial_phase_raw}")
    if row.route_of_administration:
        parts.append(f"给药方式：{row.route_of_administration}")
    if row.evidence_text:
        parts.append(f"证据：{row.evidence_text}")
    if row.source_url:
        parts.append(f"来源：{row.source_url}")
    return "\n".join(parts)


def _build_pipeline_meta(row, stock_name: str) -> ChunkMetadata:
    return ChunkMetadata(
        doc_type="pipeline_drug",
        doc_id=_doc_id("pipeline_drug", row.id, row.drug_name or ""),
        stock_code=row.stock_code or "",
        stock_name=stock_name,
        title=row.drug_name or "",
        category=row.therapeutic_area or "",
        drug_name=row.drug_name or "",
        indication=row.indication or "",
        trial_phase=row.trial_phase or "",
        route_of_administration=row.route_of_administration or "",
        source_type=row.source_type or "",
        source_url=row.source_url or "",
        source_table=PipelineDrug.__tablename__,
        source_pk=str(row.id),
        source_uid=row.dedup_key or f"pipeline:{row.id}",
        is_hot=1,
    )


def sync_pipeline_drugs(
    db: Session,
    stock_code: str | None = None,
    limit: int | None = None,
) -> int:
    stmt = select(PipelineDrug).where(PipelineDrug.is_active == 1)
    if stock_code:
        stmt = stmt.where(PipelineDrug.stock_code == stock_code)
    if limit:
        stmt = stmt.limit(limit)

    rows = db.execute(stmt).scalars().all()
    stock_name_by_code = _stock_name_map(db, [getattr(r, "stock_code", "") for r in rows])

    total = 0
    for row in rows:
        text = _pipeline_drug_text(row)
        if not text:
            continue
        meta = _build_pipeline_meta(row, stock_name_by_code.get(row.stock_code or "", ""))
        total += _write_document(db, text, "pipeline_drug", meta, row)
    return total


def sync_pipeline_drugs_by_ids(db: Session, source_ids: list[int]) -> int:
    if not source_ids:
        return 0
    stmt = select(PipelineDrug).where(PipelineDrug.id.in_(source_ids))
    rows = db.execute(stmt).scalars().all()
    stock_name_by_code = _stock_name_map(db, [getattr(r, "stock_code", "") for r in rows])

    total = 0
    for row in rows:
        text = _pipeline_drug_text(row)
        if not text:
            continue
        meta = _build_pipeline_meta(row, stock_name_by_code.get(row.stock_code or "", ""))
        total += _write_document(db, text, "pipeline_drug", meta, row)
    return total
