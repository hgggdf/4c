"""真正的批量向量回填脚本 — 全量重建 + 每日增量两种场景。

设计权衡（vs 现有 backfill_vector_store.py）：
- 大批量 embedding：把 doc 的 chunk 攒成一批一次 model.encode，避免 sentence_transformers
  的 per-call 开销。
- 大批量 chroma upsert：每 BULK_SIZE chunks 一次 collection.upsert。
- 大批量 SQL：vector_document_index 用 bulk_insert_mappings。
- 不写 TF-IDF fallback。

两种模式：
- `--full`（默认）：清空 chroma collection 和 vector_document_index 对应 doc_type 的行，
  然后处理所有源表行。
- `--incremental`：只处理源表中 vector_status IN ('pending','failed') 的行，
  跨记录批量删旧 chunks，再批量 embed/upsert，处理完把源表 vector_status 标 success。
  对没有 vector_status 的表（financial_notes / company）增量模式会跳过。

⚠️ 增量同步的单条接口（sync_*_by_ids）仍走 sync.py 原路径，不受影响。

使用：
    python scripts/bulk_backfill.py            # 全量重建
    python scripts/bulk_backfill.py --incremental    # 仅处理 pending 行
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.database.models.announcement_hot import AnnouncementRawHot
from app.core.database.models.company import CompanyMaster, CompanyProfile
from app.core.database.models.financial_hot import FinancialNotesHot
from app.core.database.models.news_hot import NewsRawHot
from app.core.database.models.pipeline import PipelineDrug
from app.core.database.models.research_report_hot import ResearchReportHot
from app.core.database.models.vector_and_job import VectorDocumentIndex
from app.core.database.session import SessionLocal
from app.knowledge.store import (
    ACTIVE_COLLECTIONS,
    EMBEDDING_MODEL_NAME,
    _embed,
    _get_collection,
    chunk_text,
    get_vector_store,
)
from app.knowledge.sync import (
    _doc_id,
    _financial_note_text,
    _load_announcement_metadata,
    _load_news_related_metadata,
    _normalize_text,
    _parse_publish_time,
    _pipeline_drug_text,
    _resolve_industry_name,
    _safe_attr,
    _source_id_for_index,
    _source_uid,
    _stock_name_map,
)
from app.paths import CHROMA_DB_DIR

BULK_EMBED_SIZE = 512          # 单批 embedding 的 chunk 数
BULK_INSERT_SIZE = 1000        # 单批 vector_document_index 写入数


def _make_chunks(text: str, base_doc_id: str, base_meta: dict[str, Any]) -> list[dict[str, Any]]:
    """把单文档切块、生成 (id, text, meta, chunk_index) 列表。"""
    pieces = chunk_text(text)
    out: list[dict[str, Any]] = []
    for i, piece in enumerate(pieces):
        cid = hashlib.md5(f"{base_doc_id}_{i}_{piece}".encode("utf-8")).hexdigest()
        meta = dict(base_meta)
        meta["chunk_index"] = i
        out.append({
            "id": cid,
            "text": piece,
            "meta": meta,
            "chunk_index": i,
        })
    return out


def _bulk_flush(
    *,
    collection,
    chunks: list[dict[str, Any]],
    db: Session,
    publish_time_by_doc_id: dict[str, Any],
    chunk_to_doc: list[tuple[str, str, str, str, str, str]],
) -> int:
    """把累积的 chunk 一次性 embed + upsert + 写索引。

    chunk_to_doc[i] = (doc_type, source_table, source_pk_str, source_uid, stock_code, industry_code, title)
    使用与 chunks 等长的并行列表，避免每个 chunk 复制大字段。
    """
    if not chunks:
        return 0

    documents = [c["text"] for c in chunks]
    metadatas = [c["meta"] for c in chunks]
    ids = [c["id"] for c in chunks]

    embeddings = _embed(documents)
    # Chroma upsert：chunk ID 确定性生成，相同 ID 直接覆盖，无需先删
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    # 先按 source_id 删旧的 vector_document_index 行，再批量插入新行
    # 比 _purge_by_source_uids 快得多：纯 SQL，不查 Chroma
    source_ids_in_batch = list({
        _source_id_for_index(ct[2], ct[3])
        for ct in chunk_to_doc
        if ct[2] or ct[3]
    })
    if source_ids_in_batch:
        doc_type_in_batch = chunk_to_doc[0][0]
        db.execute(
            delete(VectorDocumentIndex).where(
                VectorDocumentIndex.doc_type == doc_type_in_batch,
                VectorDocumentIndex.source_id.in_(source_ids_in_batch),
            )
        )
        db.flush()

    rows: list[dict[str, Any]] = []
    for i, chunk in enumerate(chunks):
        doc_type, source_table, source_pk, source_uid, stock_code, industry_code, title = chunk_to_doc[i]
        rows.append({
            "doc_type": doc_type,
            "source_table": source_table,
            "source_id": _source_id_for_index(source_pk, source_uid),
            "source_uid": source_uid or None,
            "stock_code": stock_code or None,
            "industry_code": industry_code or None,
            "title": title or None,
            "publish_time": publish_time_by_doc_id.get(chunk["meta"].get("doc_id", ""), None),
            "chunk_index": int(chunk["chunk_index"]),
            "chunk_text": chunk["text"],
            "vector_collection": ACTIVE_COLLECTIONS.get(doc_type),
            "vector_id": chunk["id"],
            "embedding_model": EMBEDDING_MODEL_NAME,
            "vector_status": "success",
        })

    for i in range(0, len(rows), BULK_INSERT_SIZE):
        batch = rows[i:i + BULK_INSERT_SIZE]
        db.bulk_insert_mappings(VectorDocumentIndex, batch)
    db.flush()

    # 把刚写入的索引行的 created_at 更新为当前时间，确保 >= 源表 updated_at
    # 避免 financial_note / company 等无 vector_status 字段的表在下次增量时被误判为"需要重建"
    if source_ids_in_batch:
        db.execute(
            update(VectorDocumentIndex)
            .where(
                VectorDocumentIndex.doc_type == doc_type_in_batch,
                VectorDocumentIndex.source_id.in_(source_ids_in_batch),
            )
            .values(created_at=datetime.now())
        )
        db.flush()

    return len(chunks)


def _purge_doc_type(db: Session, doc_type: str) -> None:
    """全量回填前清空指定 doc_type 的旧数据。"""
    # 1. 清 chroma collection（按 collection 名）
    collection_name = ACTIVE_COLLECTIONS.get(doc_type)
    if collection_name:
        try:
            collection = _get_collection(collection_name)
            existing = collection.get(include=[])
            ids = existing.get("ids") or []
            if ids:
                # 分批 delete 避免一次太大
                for i in range(0, len(ids), BULK_INSERT_SIZE):
                    collection.delete(ids=ids[i:i + BULK_INSERT_SIZE])
        except Exception as exc:  # noqa: BLE001
            print(f"  warn: chroma purge {collection_name} failed: {exc}", flush=True)

    # 2. 清 vector_document_index 中该 doc_type 的行
    db.execute(delete(VectorDocumentIndex).where(VectorDocumentIndex.doc_type == doc_type))
    db.flush()


def _purge_by_source_uids(db: Session, doc_type: str, source_uids: list[str]) -> None:
    """增量场景下，按 source_uid 批量删除旧 chunks 与索引。

    避免单条 delete_by_source 带来的 chroma 多次 query+delete 开销。
    """
    if not source_uids:
        return
    uids = [u for u in source_uids if u]
    if not uids:
        return

    collection_name = ACTIVE_COLLECTIONS.get(doc_type)
    if collection_name:
        try:
            collection = _get_collection(collection_name)
            # chroma where 的 $in 一次最多支持几千个，分批
            for i in range(0, len(uids), 500):
                batch = uids[i:i + 500]
                existing = collection.get(where={"source_uid": {"$in": batch}}, include=[])
                old_ids = existing.get("ids") or []
                if old_ids:
                    for j in range(0, len(old_ids), BULK_INSERT_SIZE):
                        collection.delete(ids=old_ids[j:j + BULK_INSERT_SIZE])
        except Exception as exc:  # noqa: BLE001
            print(f"  warn: chroma incremental purge {collection_name} failed: {exc}", flush=True)

    # vector_document_index 按 doc_type + source_uid 删
    db.execute(
        delete(VectorDocumentIndex).where(
            VectorDocumentIndex.doc_type == doc_type,
            VectorDocumentIndex.source_uid.in_(uids),
        )
    )
    db.flush()


def _latest_index_created_at_by_uid(db: Session, doc_type: str, source_uids: list[str]) -> dict[str, Any]:
    if not source_uids:
        return {}
    latest: dict[str, Any] = {}
    uids = [u for u in source_uids if u]
    for i in range(0, len(uids), 500):
        batch = uids[i:i + 500]
        rows = db.execute(
            select(
                VectorDocumentIndex.source_uid,
                func.max(VectorDocumentIndex.created_at),
            )
            .where(
                VectorDocumentIndex.doc_type == doc_type,
                VectorDocumentIndex.source_uid.in_(batch),
            )
            .group_by(VectorDocumentIndex.source_uid)
        ).all()
        for source_uid, created_at in rows:
            if source_uid:
                latest[str(source_uid)] = created_at
    return latest


def _needs_incremental_rebuild(row: Any, indexed_at_by_uid: dict[str, Any], source_uid: str) -> bool:
    indexed_at = indexed_at_by_uid.get(source_uid)
    if indexed_at is None:
        return True
    updated_at = getattr(row, "updated_at", None)
    return bool(updated_at and updated_at > indexed_at)


def _mark_status(db: Session, model: Any, ids: list[Any], status: str) -> None:
    """批量更新源表 vector_status。仅对有 vector_status 字段的 model 生效。"""
    if not ids or not hasattr(model, "vector_status"):
        return
    pk_col = getattr(model, "id", None) or getattr(model, "stock_code", None)
    if pk_col is None:
        return
    db.execute(update(model).where(pk_col.in_(ids)).values(vector_status=status))
    db.flush()


def _build_meta(*, doc_type: str, doc_id: str, **kwargs: Any) -> dict[str, Any]:
    """构造与 ChunkMetadata 一致的 dict（替代 dataclass，省一次 to_dict）。"""
    base = {
        "doc_type": doc_type,
        "doc_id": doc_id,
        "stock_code": "",
        "stock_name": "",
        "title": "",
        "publish_date": "",
        "category": "",
        "topic_category": "",
        "signal_type": "",
        "risk_level": "",
        "impact_level": "",
        "impact_direction": "",
        "impact_horizon": "",
        "source_type": "",
        "source_url": "",
        "source_table": "",
        "source_pk": "",
        "source_uid": "",
        "industry_code": "",
        "industry_name": "",
        "drug_name": "",
        "indication": "",
        "trial_phase": "",
        "route_of_administration": "",
        "event_type": "",
        "is_hot": 1,
    }
    base.update({k: v for k, v in kwargs.items() if v is not None})
    return {k: ("" if v is None else v) for k, v in base.items()}


# ── 各 doc_type 的回填函数 ─────────────────────────────────

INCREMENTAL_STATUSES = ("pending", "failed")


def _mark_skipped_empty(db: Session, model: Any, ids: list[Any]) -> None:
    """空 content 的行标记 skipped_empty，避免每次增量都重复扫到。"""
    if not ids or not hasattr(model, "vector_status"):
        return
    pk_col = getattr(model, "id", None) or getattr(model, "stock_code", None)
    if pk_col is None:
        return
    db.execute(update(model).where(pk_col.in_(ids)).values(vector_status="skipped_empty"))
    db.flush()


def backfill_announcements(db: Session, collection, *, incremental: bool = False) -> int:
    stmt = select(AnnouncementRawHot)
    if incremental:
        stmt = stmt.where(AnnouncementRawHot.vector_status.in_(INCREMENTAL_STATUSES))
    rows = db.execute(stmt).scalars().all()
    if not rows:
        return 0
    stock_map = _stock_name_map(db, [getattr(r, "stock_code", "") for r in rows])

    pending_chunks: list[dict[str, Any]] = []
    pending_meta: list[tuple[str, str, str, str, str, str, str]] = []
    publish_time_by_doc_id: dict[str, Any] = {}
    processed_ids: list[Any] = []
    skipped_ids: list[Any] = []
    total = 0

    for row in rows:
        content = _normalize_text(_safe_attr(row, "content")) or _normalize_text(_safe_attr(row, "summary_text"))
        if not content:
            skipped_ids.append(row.id)
            continue

        # bulk_backfill 跳过 _load_announcement_metadata（N+1 查询，扩展表已废弃，实际返回全空）
        extra = {
            "category": _safe_attr(row, "announcement_type", "") or "",
            "signal_type": "", "risk_level": "", "drug_name": "",
            "indication": "", "trial_phase": "", "event_type": "",
        }
        doc_id = _doc_id("announcement", row.id, content)
        publish_date_str = str(_safe_attr(row, "publish_date", "") or "")
        publish_time_by_doc_id[doc_id] = _parse_publish_time(publish_date_str)
        source_table = AnnouncementRawHot.__tablename__
        source_pk = str(row.id)
        source_uid = _source_uid(row, "announcement")
        stock_code = _safe_attr(row, "stock_code", "") or ""

        meta = _build_meta(
            doc_type="announcement",
            doc_id=doc_id,
            stock_code=stock_code,
            stock_name=stock_map.get(stock_code, ""),
            title=_safe_attr(row, "title", "") or "",
            publish_date=publish_date_str,
            category=extra["category"],
            signal_type=extra["signal_type"],
            risk_level=extra["risk_level"],
            drug_name=extra["drug_name"],
            indication=extra["indication"],
            trial_phase=extra["trial_phase"],
            event_type=extra["event_type"],
            source_type=_safe_attr(row, "source_type", "") or "",
            source_url=_safe_attr(row, "source_url", "") or "",
            source_table=source_table,
            source_pk=source_pk,
            source_uid=source_uid,
            is_hot=1,
        )

        new_chunks = _make_chunks(content, doc_id, meta)
        title = _safe_attr(row, "title", "") or ""
        for c in new_chunks:
            pending_chunks.append(c)
            pending_meta.append(("announcement", source_table, source_pk, source_uid, stock_code, "", title))
        processed_ids.append(row.id)

        if len(pending_chunks) >= BULK_EMBED_SIZE:
            total += _bulk_flush(
                collection=collection,
                chunks=pending_chunks,
                db=db,
                publish_time_by_doc_id=publish_time_by_doc_id,
                chunk_to_doc=pending_meta,
            )
            pending_chunks, pending_meta = [], []
            print(f"  announcement: {total} chunks flushed", flush=True)

    if pending_chunks:
        total += _bulk_flush(
            collection=collection,
            chunks=pending_chunks,
            db=db,
            publish_time_by_doc_id=publish_time_by_doc_id,
            chunk_to_doc=pending_meta,
        )

    _mark_status(db, AnnouncementRawHot, processed_ids, "success")
    _mark_skipped_empty(db, AnnouncementRawHot, skipped_ids)
    print(f"  announcement done: {len(rows)} rows -> {total} chunks", flush=True)
    return total


def backfill_financial_notes(db: Session, collection, *, incremental: bool = False) -> int:
    if incremental:
        # financial_notes_hot 没有 vector_status 字段；增量模式无法判定新增，跳过。
        pass
    rows = db.execute(select(FinancialNotesHot)).scalars().all()
    if incremental:
        uid_by_id = {row.id: _source_uid(row, "financial") for row in rows}
        indexed_at_by_uid = _latest_index_created_at_by_uid(db, "financial_note", list(uid_by_id.values()))
        rows = [
            row for row in rows
            if _financial_note_text(row)
            and _needs_incremental_rebuild(row, indexed_at_by_uid, uid_by_id[row.id])
        ]
    if not rows:
        return 0
    stock_map = _stock_name_map(db, [getattr(r, "stock_code", "") for r in rows])

    pending_chunks: list[dict[str, Any]] = []
    pending_meta: list[tuple[str, str, str, str, str, str, str]] = []
    publish_time_by_doc_id: dict[str, Any] = {}
    total = 0

    for row in rows:
        text_value = _financial_note_text(row)
        if not text_value:
            continue  # financial_notes 无 vector_status，无需标记

        doc_id = _doc_id("financial_note", row.id, text_value)
        publish_date_str = str(_safe_attr(row, "report_date", "") or "")
        publish_time_by_doc_id[doc_id] = _parse_publish_time(publish_date_str)
        source_table = FinancialNotesHot.__tablename__
        source_pk = str(row.id)
        source_uid = _source_uid(row, "financial")
        stock_code = _safe_attr(row, "stock_code", "") or ""

        meta = _build_meta(
            doc_type="financial_note",
            doc_id=doc_id,
            stock_code=stock_code,
            stock_name=stock_map.get(stock_code, ""),
            publish_date=publish_date_str,
            category=_safe_attr(row, "note_type", "") or _safe_attr(row, "report_type", "") or "",
            source_type=_safe_attr(row, "source_type", "") or "",
            source_url=_safe_attr(row, "source_url", "") or "",
            source_table=source_table,
            source_pk=source_pk,
            source_uid=source_uid,
            is_hot=1,
        )

        new_chunks = _make_chunks(text_value, doc_id, meta)
        for c in new_chunks:
            pending_chunks.append(c)
            pending_meta.append(("financial_note", source_table, source_pk, source_uid, stock_code, "", ""))

        if len(pending_chunks) >= BULK_EMBED_SIZE:
            total += _bulk_flush(
                collection=collection,
                chunks=pending_chunks,
                db=db,
                publish_time_by_doc_id=publish_time_by_doc_id,
                chunk_to_doc=pending_meta,
            )
            pending_chunks, pending_meta = [], []
            print(f"  financial_note: {total} chunks flushed", flush=True)

    if pending_chunks:
        total += _bulk_flush(
            collection=collection,
            chunks=pending_chunks,
            db=db,
            publish_time_by_doc_id=publish_time_by_doc_id,
            chunk_to_doc=pending_meta,
        )

    print(f"  financial_note done: {len(rows)} rows -> {total} chunks", flush=True)
    return total


def backfill_news(db: Session, collection, *, incremental: bool = False) -> int:
    stmt = select(NewsRawHot)
    if incremental:
        stmt = stmt.where(NewsRawHot.vector_status.in_(INCREMENTAL_STATUSES))
    rows = db.execute(stmt).scalars().all()
    if not rows:
        return 0

    pending_chunks: list[dict[str, Any]] = []
    pending_meta: list[tuple[str, str, str, str, str, str, str]] = []
    publish_time_by_doc_id: dict[str, Any] = {}
    stock_name_by_code: dict[str, str] = {}
    processed_ids: list[Any] = []
    skipped_ids: list[Any] = []
    total = 0

    for row in rows:
        content = _normalize_text(_safe_attr(row, "content"))
        if not content:
            skipped_ids.append(row.id)
            continue

        extra = _load_news_related_metadata(db, row, is_hot=True)
        stock_code = extra["stock_code"]
        if stock_code and stock_code not in stock_name_by_code:
            stock_name_by_code.update(_stock_name_map(db, [stock_code]))

        doc_id = _doc_id("news", row.id, content)
        publish_time = _safe_attr(row, "publish_time", None)
        publish_date_str = str(publish_time.date()) if publish_time else ""
        publish_time_by_doc_id[doc_id] = _parse_publish_time(publish_date_str or publish_time)

        source_table = NewsRawHot.__tablename__
        source_pk = str(row.id)
        source_uid = _source_uid(row, "news")

        meta = _build_meta(
            doc_type="news",
            doc_id=doc_id,
            stock_code=stock_code,
            stock_name=stock_name_by_code.get(stock_code, ""),
            title=_safe_attr(row, "title", "") or "",
            publish_date=publish_date_str,
            category=extra["topic_category"],
            topic_category=extra["topic_category"],
            signal_type=extra["signal_type"],
            impact_level=extra["impact_level"],
            impact_direction=extra["impact_direction"],
            impact_horizon=extra["impact_horizon"],
            source_type=_safe_attr(row, "source_name", "") or _safe_attr(row, "source_type", "") or "",
            source_url=_safe_attr(row, "source_url", "") or "",
            source_table=source_table,
            source_pk=source_pk,
            source_uid=source_uid,
            industry_code=extra["industry_code"],
            industry_name=extra["industry_name"],
            is_hot=1,
        )

        new_chunks = _make_chunks(content, doc_id, meta)
        title = _safe_attr(row, "title", "") or ""
        for c in new_chunks:
            pending_chunks.append(c)
            pending_meta.append(("news", source_table, source_pk, source_uid, stock_code, extra["industry_code"], title))
        processed_ids.append(row.id)

        if len(pending_chunks) >= BULK_EMBED_SIZE:
            total += _bulk_flush(
                collection=collection,
                chunks=pending_chunks,
                db=db,
                publish_time_by_doc_id=publish_time_by_doc_id,
                chunk_to_doc=pending_meta,
            )
            pending_chunks, pending_meta = [], []
            print(f"  news: {total} chunks flushed", flush=True)

    if pending_chunks:
        total += _bulk_flush(
            collection=collection,
            chunks=pending_chunks,
            db=db,
            publish_time_by_doc_id=publish_time_by_doc_id,
            chunk_to_doc=pending_meta,
        )

    _mark_status(db, NewsRawHot, processed_ids, "success")
    _mark_skipped_empty(db, NewsRawHot, skipped_ids)
    print(f"  news done: {len(rows)} rows -> {total} chunks", flush=True)
    return total


def backfill_research_reports(db: Session, collection, *, incremental: bool = False) -> int:
    stmt = select(ResearchReportHot)
    if incremental:
        stmt = stmt.where(ResearchReportHot.vector_status.in_(INCREMENTAL_STATUSES))
    rows = db.execute(stmt).scalars().all()
    if not rows:
        return 0
    stock_map = _stock_name_map(db, [getattr(r, "stock_code", "") for r in rows])

    pending_chunks: list[dict[str, Any]] = []
    pending_meta: list[tuple[str, str, str, str, str, str, str]] = []
    publish_time_by_doc_id: dict[str, Any] = {}
    processed_ids: list[Any] = []
    skipped_ids: list[Any] = []
    total = 0

    for row in rows:
        content = _normalize_text(_safe_attr(row, "content")) or _normalize_text(_safe_attr(row, "summary_text"))
        if not content:
            skipped_ids.append(row.id)
            continue

        stock_code = _safe_attr(row, "stock_code", "") or ""
        industry_code = _safe_attr(row, "industry_code", "") or ""
        industry_name = _resolve_industry_name(db, industry_code) if industry_code else ""
        doc_id = _doc_id("report", row.id, content)
        publish_date_str = str(_safe_attr(row, "publish_date", "") or "")
        publish_time_by_doc_id[doc_id] = _parse_publish_time(publish_date_str)

        source_table = ResearchReportHot.__tablename__
        source_pk = str(row.id)
        source_uid = _source_uid(row, "research_report")

        meta = _build_meta(
            doc_type="report",
            doc_id=doc_id,
            stock_code=stock_code,
            stock_name=stock_map.get(stock_code, ""),
            title=_safe_attr(row, "title", "") or "",
            publish_date=publish_date_str,
            category=_safe_attr(row, "scope_type", "") or "",
            source_type=_safe_attr(row, "source_type", "") or "",
            source_url=_safe_attr(row, "source_url", "") or "",
            source_table=source_table,
            source_pk=source_pk,
            source_uid=source_uid,
            industry_code=industry_code,
            industry_name=industry_name,
            is_hot=1,
        )

        new_chunks = _make_chunks(content, doc_id, meta)
        title = _safe_attr(row, "title", "") or ""
        for c in new_chunks:
            pending_chunks.append(c)
            pending_meta.append(("report", source_table, source_pk, source_uid, stock_code, industry_code, title))
        processed_ids.append(row.id)

        if len(pending_chunks) >= BULK_EMBED_SIZE:
            total += _bulk_flush(
                collection=collection,
                chunks=pending_chunks,
                db=db,
                publish_time_by_doc_id=publish_time_by_doc_id,
                chunk_to_doc=pending_meta,
            )
            pending_chunks, pending_meta = [], []
            print(f"  report: {total} chunks flushed", flush=True)

    if pending_chunks:
        total += _bulk_flush(
            collection=collection,
            chunks=pending_chunks,
            db=db,
            publish_time_by_doc_id=publish_time_by_doc_id,
            chunk_to_doc=pending_meta,
        )

    _mark_status(db, ResearchReportHot, processed_ids, "success")
    _mark_skipped_empty(db, ResearchReportHot, skipped_ids)
    print(f"  report done: {len(rows)} rows -> {total} chunks", flush=True)
    return total


def backfill_company_profiles(db: Session, collection, *, incremental: bool = False) -> int:
    if incremental:
        # company 没有 vector_status 字段；增量模式跳过（通常变化很少）。
        pass
    rows = db.execute(select(CompanyMaster)).scalars().all()
    if incremental:
        uid_by_code = {
            row.stock_code: f"company:{row.stock_code}"
            for row in rows
            if getattr(row, "stock_code", None)
        }
        indexed_at_by_uid = _latest_index_created_at_by_uid(db, "company_profile", list(uid_by_code.values()))
        rows = [
            row for row in rows
            if getattr(row, "stock_code", None)
            and any([row.business_summary, row.market_position, row.management_summary])
            and _needs_incremental_rebuild(row, indexed_at_by_uid, uid_by_code[row.stock_code])
        ]
    if not rows:
        return 0

    pending_chunks: list[dict[str, Any]] = []
    pending_meta: list[tuple[str, str, str, str, str, str, str]] = []
    publish_time_by_doc_id: dict[str, Any] = {}
    total = 0

    for profile in rows:
        stock_name = getattr(profile, "stock_name", "") or ""
        parts = [p for p in [profile.business_summary, profile.market_position, profile.management_summary] if p]
        if not parts:
            continue

        text = "\n".join(parts)
        doc_id = _doc_id("company_profile", profile.stock_code, text)
        publish_time_by_doc_id[doc_id] = None
        source_table = CompanyProfile.__tablename__
        source_pk = profile.stock_code or ""
        source_uid = f"company:{profile.stock_code}"

        meta = _build_meta(
            doc_type="company_profile",
            doc_id=doc_id,
            stock_code=profile.stock_code or "",
            stock_name=stock_name,
            title=stock_name,
            source_table=source_table,
            source_pk=source_pk,
            source_uid=source_uid,
            is_hot=1,
        )

        new_chunks = _make_chunks(text, doc_id, meta)
        for c in new_chunks:
            pending_chunks.append(c)
            pending_meta.append(("company_profile", source_table, source_pk, source_uid, profile.stock_code or "", "", stock_name))

        if len(pending_chunks) >= BULK_EMBED_SIZE:
            total += _bulk_flush(
                collection=collection,
                chunks=pending_chunks,
                db=db,
                publish_time_by_doc_id=publish_time_by_doc_id,
                chunk_to_doc=pending_meta,
            )
            pending_chunks, pending_meta = [], []

    if pending_chunks:
        total += _bulk_flush(
            collection=collection,
            chunks=pending_chunks,
            db=db,
            publish_time_by_doc_id=publish_time_by_doc_id,
            chunk_to_doc=pending_meta,
        )

    print(f"  company_profile done: {len(rows)} rows -> {total} chunks", flush=True)
    return total


def backfill_pipeline_drugs(db: Session, collection, *, incremental: bool = False) -> int:
    stmt = select(PipelineDrug).where(PipelineDrug.is_active == 1)
    if incremental:
        stmt = stmt.where(PipelineDrug.vector_status.in_(INCREMENTAL_STATUSES))
    rows = db.execute(stmt).scalars().all()
    if not rows:
        return 0
    stock_map = _stock_name_map(db, [getattr(r, "stock_code", "") for r in rows])

    pending_chunks: list[dict[str, Any]] = []
    pending_meta: list[tuple[str, str, str, str, str, str, str]] = []
    publish_time_by_doc_id: dict[str, Any] = {}
    processed_ids: list[Any] = []
    skipped_ids: list[Any] = []
    total = 0

    for row in rows:
        text_value = _pipeline_drug_text(row)
        if not text_value:
            skipped_ids.append(row.id)
            continue

        doc_id = _doc_id("pipeline_drug", row.id, row.drug_name or "")
        publish_time_by_doc_id[doc_id] = None
        source_table = PipelineDrug.__tablename__
        source_pk = str(row.id)
        source_uid = row.dedup_key or f"pipeline:{row.id}"
        stock_code = row.stock_code or ""

        meta = _build_meta(
            doc_type="pipeline_drug",
            doc_id=doc_id,
            stock_code=stock_code,
            stock_name=stock_map.get(stock_code, ""),
            title=row.drug_name or "",
            category=row.therapeutic_area or "",
            drug_name=row.drug_name or "",
            indication=row.indication or "",
            trial_phase=row.trial_phase or "",
            route_of_administration=row.route_of_administration or "",
            source_type=row.source_type or "",
            source_url=row.source_url or "",
            source_table=source_table,
            source_pk=source_pk,
            source_uid=source_uid,
            is_hot=1,
        )

        new_chunks = _make_chunks(text_value, doc_id, meta)
        for c in new_chunks:
            pending_chunks.append(c)
            pending_meta.append(("pipeline_drug", source_table, source_pk, source_uid, stock_code, "", row.drug_name or ""))
        processed_ids.append(row.id)

        if len(pending_chunks) >= BULK_EMBED_SIZE:
            total += _bulk_flush(
                collection=collection,
                chunks=pending_chunks,
                db=db,
                publish_time_by_doc_id=publish_time_by_doc_id,
                chunk_to_doc=pending_meta,
            )
            pending_chunks, pending_meta = [], []

    if pending_chunks:
        total += _bulk_flush(
            collection=collection,
            chunks=pending_chunks,
            db=db,
            publish_time_by_doc_id=publish_time_by_doc_id,
            chunk_to_doc=pending_meta,
        )

    _mark_status(db, PipelineDrug, processed_ids, "success")
    _mark_skipped_empty(db, PipelineDrug, skipped_ids)
    print(f"  pipeline_drug done: {len(rows)} rows -> {total} chunks", flush=True)
    return total


# ── 入口 ─────────────────────────────────────────────────

BACKFILL_PLAN = [
    ("announcement", backfill_announcements),
    ("financial_note", backfill_financial_notes),
    ("news", backfill_news),
    ("report", backfill_research_reports),
    ("company_profile", backfill_company_profiles),
    ("pipeline_drug", backfill_pipeline_drugs),
]


def run_bulk_backfill(*, incremental: bool = False) -> dict:
    started = time.time()
    step_counts: dict[str, int] = {}
    step_seconds: dict[str, float] = {}
    mode = "incremental" if incremental else "full"

    with SessionLocal() as db:
        try:
            for doc_type, fn in BACKFILL_PLAN:
                t0 = time.time()
                if not incremental:
                    print(f"[{doc_type}] purging old data...", flush=True)
                    _purge_doc_type(db, doc_type)
                collection = _get_collection(ACTIVE_COLLECTIONS[doc_type])
                print(f"[{doc_type}] backfilling ({mode})...", flush=True)
                step_counts[doc_type] = fn(db, collection, incremental=incremental)
                step_seconds[doc_type] = round(time.time() - t0, 2)
                db.commit()
            db.commit()
        except Exception:
            db.rollback()
            raise

    vector_store = get_vector_store()
    collection_counts = {dt: vector_store.count(doc_type=dt) for dt, _ in BACKFILL_PLAN}

    return {
        "mode": mode,
        "chroma_path": str(CHROMA_DB_DIR),
        "step_counts": step_counts,
        "step_seconds": step_seconds,
        "collection_counts": collection_counts,
        "total_backfilled_chunks": sum(step_counts.values()),
        "total_seconds": round(time.time() - started, 2),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Bulk vector backfill (full or incremental).")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="只处理 vector_status IN ('pending','failed') 的源行；不清空 collection。",
    )
    args = parser.parse_args()

    result = run_bulk_backfill(incremental=args.incremental)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
