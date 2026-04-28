"""Fast backfill: upsert-only, no per-document delete scan."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database.session import SessionLocal
from app.core.database.models.announcement_hot import (
    AnnouncementRawHot,
    AnnouncementStructuredHot,
    CentralizedProcurementEventHot,
    ClinicalTrialEventHot,
    DrugApprovalHot,
    RegulatoryRiskEventHot,
)
from app.core.database.models.company import CompanyMaster, CompanyProfile
from app.core.database.models.financial_hot import FinancialNotesHot
from app.knowledge.store import (
    _get_collection,
    _get_collection_name,
    _embed,
    chunk_text,
    ACTIVE_COLLECTIONS,
    get_vector_store,
)
from app.knowledge.sync import (
    _doc_id,
    _safe_attr,
    _normalize_text,
    _stock_name_map,
    _load_announcement_metadata,
    _choose_first_text,
)

BATCH_SIZE = 50  # upsert N docs at a time


def _upsert_batch(collection, texts_list, metadatas_list, doc_ids_list):
    """Chunk all texts, embed in one shot, upsert."""
    all_chunks, all_metas, all_ids = [], [], []
    for text, meta, base_id in zip(texts_list, metadatas_list, doc_ids_list):
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            cid = hashlib.md5(f"{base_id}_{i}_{chunk}".encode()).hexdigest()
            m = dict(meta)
            m["chunk_index"] = i
            all_chunks.append(chunk)
            all_metas.append(m)
            all_ids.append(cid)

    if not all_chunks:
        return 0

    embeddings = _embed(all_chunks)
    collection.upsert(
        ids=all_ids,
        embeddings=embeddings,
        documents=all_chunks,
        metadatas=all_metas,
    )
    return len(all_chunks)


def backfill_announcements(db: Session) -> int:
    collection = _get_collection(_get_collection_name("announcement"))
    rows = db.execute(select(AnnouncementRawHot)).scalars().all()
    stock_map = _stock_name_map(db, [getattr(r, "stock_code", "") for r in rows])

    total = 0
    batch_texts, batch_metas, batch_ids = [], [], []

    for i, row in enumerate(rows):
        content = _normalize_text(_safe_attr(row, "content"))
        if not content:
            continue

        extra = _load_announcement_metadata(db, row, is_hot=True)
        doc_id = _doc_id("announcement", row.id, content)
        meta = {
            "doc_type": "announcement",
            "doc_id": doc_id,
            "stock_code": _safe_attr(row, "stock_code", "") or "",
            "stock_name": stock_map.get(_safe_attr(row, "stock_code", "") or "", ""),
            "title": _safe_attr(row, "title", "") or "",
            "publish_date": str(_safe_attr(row, "publish_date", "") or ""),
            "category": extra["category"],
            "signal_type": extra["signal_type"],
            "risk_level": extra["risk_level"],
            "drug_name": extra["drug_name"],
            "indication": extra["indication"],
            "trial_phase": extra["trial_phase"],
            "event_type": extra["event_type"],
            "source_type": _safe_attr(row, "source_type", "") or "",
            "source_url": _safe_attr(row, "source_url", "") or "",
            "source_table": AnnouncementRawHot.__tablename__,
            "source_pk": str(row.id),
            "is_hot": 1,
        }
        batch_texts.append(content)
        batch_metas.append(meta)
        batch_ids.append(doc_id)

        if len(batch_texts) >= BATCH_SIZE:
            total += _upsert_batch(collection, batch_texts, batch_metas, batch_ids)
            batch_texts, batch_metas, batch_ids = [], [], []
            print(f"  announcements: {i+1}/{len(rows)} rows, {total} chunks", flush=True)

    if batch_texts:
        total += _upsert_batch(collection, batch_texts, batch_metas, batch_ids)

    print(f"  announcements done: {len(rows)} rows, {total} chunks", flush=True)
    return total


def backfill_financial_notes(db: Session) -> int:
    collection = _get_collection(_get_collection_name("financial_note"))
    rows = db.execute(select(FinancialNotesHot)).scalars().all()
    stock_map = _stock_name_map(db, [getattr(r, "stock_code", "") for r in rows])

    total = 0
    batch_texts, batch_metas, batch_ids = [], [], []

    for row in rows:
        text = _normalize_text(_safe_attr(row, "note_text"))
        if not text:
            continue

        doc_id = _doc_id("financial_note", row.id, text)
        meta = {
            "doc_type": "financial_note",
            "doc_id": doc_id,
            "stock_code": _safe_attr(row, "stock_code", "") or "",
            "stock_name": stock_map.get(_safe_attr(row, "stock_code", "") or "", ""),
            "publish_date": str(_safe_attr(row, "report_date", "") or ""),
            "category": _safe_attr(row, "note_type", "") or "",
            "source_type": _safe_attr(row, "source_type", "") or "",
            "source_url": _safe_attr(row, "source_url", "") or "",
            "source_table": FinancialNotesHot.__tablename__,
            "source_pk": str(row.id),
            "is_hot": 1,
        }
        batch_texts.append(text)
        batch_metas.append(meta)
        batch_ids.append(doc_id)

        if len(batch_texts) >= BATCH_SIZE:
            total += _upsert_batch(collection, batch_texts, batch_metas, batch_ids)
            batch_texts, batch_metas, batch_ids = [], [], []

    if batch_texts:
        total += _upsert_batch(collection, batch_texts, batch_metas, batch_ids)

    print(f"  financial_notes done: {len(rows)} rows, {total} chunks", flush=True)
    return total


def backfill_company_profiles(db: Session) -> int:
    collection = _get_collection(_get_collection_name("company_profile"))
    rows = db.execute(
        select(CompanyProfile, CompanyMaster.stock_name).join(
            CompanyMaster, CompanyProfile.stock_code == CompanyMaster.stock_code
        )
    ).all()

    total = 0
    batch_texts, batch_metas, batch_ids = [], [], []

    for profile, stock_name in rows:
        parts = [p for p in [profile.business_summary, profile.market_position, profile.management_summary] if p]
        if not parts:
            continue

        text = "\n".join(parts)
        doc_id = _doc_id("company_profile", profile.id, text)
        meta = {
            "doc_type": "company_profile",
            "doc_id": doc_id,
            "stock_code": profile.stock_code or "",
            "stock_name": stock_name or "",
            "source_table": CompanyProfile.__tablename__,
            "source_pk": str(profile.id),
            "is_hot": 1,
        }
        batch_texts.append(text)
        batch_metas.append(meta)
        batch_ids.append(doc_id)

        if len(batch_texts) >= BATCH_SIZE:
            total += _upsert_batch(collection, batch_texts, batch_metas, batch_ids)
            batch_texts, batch_metas, batch_ids = [], [], []

    if batch_texts:
        total += _upsert_batch(collection, batch_texts, batch_metas, batch_ids)

    print(f"  company_profiles done: {len(rows)} rows, {total} chunks", flush=True)
    return total


def main():
    step_counts = {}
    with SessionLocal() as db:
        print("Backfilling company_profiles...", flush=True)
        step_counts["company_profile"] = backfill_company_profiles(db)

        print("Backfilling announcements...", flush=True)
        step_counts["announcement"] = backfill_announcements(db)

        print("Backfilling financial_notes...", flush=True)
        step_counts["financial_note"] = backfill_financial_notes(db)

        db.commit()

    vs = get_vector_store()
    collection_counts = {dt: vs.count(doc_type=dt) for dt in ACTIVE_COLLECTIONS}

    result = {
        "step_counts": step_counts,
        "collection_counts": collection_counts,
        "total_chunks": sum(step_counts.values()),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
