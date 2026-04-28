"""向量索引一致性验证脚本。

验证维度：
1. 数量一致性 — 数据库记录数 vs Chroma chunk 数
2. 内容溯源 — 随机采样，验证 chunk 内容确实来自对应 DB 记录
3. Metadata 完整性 — stock_code / source_pk / doc_type / title 等关键字段
4. 集合隔离 — 不同 doc_type 的 chunk 不会串到别的集合
5. 检索闭环 — 用已入库的文本片段检索，应能召回自身
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

import argparse
import hashlib
import logging
import random
from typing import Any

from sqlalchemy import func, select

from app.core.database.models.announcement_hot import AnnouncementRawHot
from app.core.database.models.company import CompanyMaster, CompanyProfile
from app.core.database.models.financial_hot import FinancialNotesHot
from app.core.database.models.news_hot import NewsRawHot
from app.core.database.session import SessionLocal
from app.knowledge.store import (
    ACTIVE_COLLECTIONS,
    VectorKnowledgeStore,
    chunk_text,
    get_vector_store,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _doc_id(prefix: str, pk: int, text: str) -> str:
    """与 sync.py 中完全一致的 doc_id 生成逻辑。"""
    return f"{prefix}_{pk}_{hashlib.md5((text or '')[:200].encode('utf-8')).hexdigest()[:10]}"


# ---------------------------------------------------------------------------
# 1. 数量一致性
# ---------------------------------------------------------------------------
def verify_counts(db, vs: VectorKnowledgeStore) -> dict[str, bool]:
    """对比 DB 记录数与 Chroma chunk 数的比例是否合理。"""
    results: dict[str, bool] = {}

    db_counts = {
        "announcement": db.execute(select(func.count()).select_from(AnnouncementRawHot)).scalar() or 0,
        "financial_note": db.execute(select(func.count()).select_from(FinancialNotesHot)).scalar() or 0,
        "news": db.execute(select(func.count()).select_from(NewsRawHot)).scalar() or 0,
        "company_profile": db.execute(select(func.count()).select_from(CompanyProfile)).scalar() or 0,
    }

    logger.info("\n" + "=" * 60)
    logger.info("【1/5】数量一致性验证")
    logger.info("=" * 60)

    for doc_type, db_count in db_counts.items():
        chroma_count = vs.count(doc_type)
        if db_count == 0:
            status = "SKIP"
            ok = chroma_count == 0
        elif chroma_count >= db_count:
            status = "PASS"
            ok = True
        else:
            status = "FAIL"
            ok = False

        results[doc_type] = ok
        marker = "✓" if ok else "✗"
        logger.info(
            f"  {marker} {doc_type:20s}  DB={db_count:>6,}  Chroma={chroma_count:>6,}  [{status}]"
        )

    logger.info(f"  结果: {sum(results.values())}/{len(results)} 通过")
    return results


# ---------------------------------------------------------------------------
# 2. Metadata 完整性
# ---------------------------------------------------------------------------
def verify_metadata(vs: VectorKnowledgeStore, sample_size: int = 20) -> bool:
    """随机抽查 chunk 的 metadata 关键字段是否完整。"""
    logger.info("\n" + "=" * 60)
    logger.info("【2/5】Metadata 完整性验证")
    logger.info("=" * 60)

    required_fields = ["doc_type", "doc_id", "stock_code", "source_table", "source_pk"]
    all_ok = True
    checked = 0

    for doc_type, collection_name in ACTIVE_COLLECTIONS.items():
        from app.knowledge.store import _get_collection

        collection = _get_collection(collection_name)
        total = collection.count()
        if total == 0:
            logger.info(f"  → {doc_type}: 空集合，跳过")
            continue

        n = min(sample_size, total)
        try:
            # Chroma peek() 是取前 N 条的简便方式
            sample = collection.peek(limit=n)
        except Exception:
            # fallback: get(limit=n)
            try:
                sample = collection.get(limit=n, include=["metadatas"])
            except Exception as exc:
                logger.warning(f"  → {doc_type}: 获取样本失败: {exc}")
                continue

        metas = sample.get("metadatas", []) or []
        bad = 0
        for meta in metas:
            checked += 1
            missing = [f for f in required_fields if not meta or meta.get(f) in (None, "")]
            if missing:
                bad += 1
                all_ok = False

        status = "PASS" if bad == 0 else "FAIL"
        marker = "✓" if bad == 0 else "✗"
        logger.info(
            f"  {marker} {doc_type:20s} 抽查{n:>3}条  缺失{bad:>2}条  [{status}]"
        )

    logger.info(f"  结果: {'通过' if all_ok else '未通过'} (共检查 {checked} 条)")
    return all_ok


# ---------------------------------------------------------------------------
# 3. 内容溯源验证
# ---------------------------------------------------------------------------
def verify_source_tracing(db, vs: VectorKnowledgeStore, sample_size: int = 10) -> bool:
    """从 DB 随机采样记录，验证其 chunk 确实写入了 Chroma。"""
    logger.info("\n" + "=" * 60)
    logger.info("【3/5】内容溯源验证")
    logger.info("=" * 60)

    all_ok = True

    # ---------- announcement ----------
    def check_announcements():
        nonlocal all_ok
        records = db.execute(select(AnnouncementRawHot)).scalars().all()
        if not records:
            logger.info("  → announcement: DB 无数据，跳过")
            return
        samples = random.sample(records, min(sample_size, len(records)))
        found = missing = 0
        for row in samples:
            content = (row.content or "").strip()
            if not content:
                continue
            doc_id = _doc_id("announcement", row.id, content)
            chunks = chunk_text(content)
            if not chunks:
                continue
            expected_ids = [
                hashlib.md5(f"{doc_id}_{i}_{c}".encode("utf-8")).hexdigest()
                for i, c in enumerate(chunks)
            ]
            from app.knowledge.store import _get_collection
            collection = _get_collection(ACTIVE_COLLECTIONS["announcement"])
            try:
                existing = collection.get(ids=expected_ids, include=[])
                retrieved = existing.get("ids", []) if existing else []
                if len(retrieved) == len(chunks):
                    found += 1
                else:
                    missing += 1
                    all_ok = False
            except Exception:
                missing += 1
                all_ok = False
        total = found + missing
        status = "PASS" if missing == 0 else "FAIL"
        marker = "✓" if missing == 0 else "✗"
        logger.info(f"  {marker} announcement:20s 采样{total:>3}条  匹配{found:>3}条  缺失{missing:>2}条  [{status}]")

    # ---------- financial_note ----------
    def check_financial_notes():
        nonlocal all_ok
        records = db.execute(select(FinancialNotesHot)).scalars().all()
        if not records:
            logger.info("  → financial_note: DB 无数据，跳过")
            return
        samples = random.sample(records, min(sample_size, len(records)))
        found = missing = 0
        for row in samples:
            text_value = (getattr(row, "content_text", None) or row.note_text or "").strip()
            if not text_value:
                continue
            doc_id = _doc_id("financial_note", row.id, text_value)
            chunks = chunk_text(text_value)
            if not chunks:
                continue
            expected_ids = [
                hashlib.md5(f"{doc_id}_{i}_{c}".encode("utf-8")).hexdigest()
                for i, c in enumerate(chunks)
            ]
            from app.knowledge.store import _get_collection
            collection = _get_collection(ACTIVE_COLLECTIONS["financial_note"])
            try:
                existing = collection.get(ids=expected_ids, include=[])
                retrieved = existing.get("ids", []) if existing else []
                if len(retrieved) == len(chunks):
                    found += 1
                else:
                    missing += 1
                    all_ok = False
            except Exception:
                missing += 1
                all_ok = False
        total = found + missing
        status = "PASS" if missing == 0 else "FAIL"
        marker = "✓" if missing == 0 else "✗"
        logger.info(f"  {marker} financial_note:20s 采样{total:>3}条  匹配{found:>3}条  缺失{missing:>2}条  [{status}]")

    # ---------- news ----------
    def check_news():
        nonlocal all_ok
        records = db.execute(select(NewsRawHot)).scalars().all()
        if not records:
            logger.info("  → news: DB 无数据，跳过")
            return
        samples = random.sample(records, min(sample_size, len(records)))
        found = missing = 0
        for row in samples:
            content = (row.content or "").strip()
            if not content:
                continue
            doc_id = _doc_id("news", row.id, content)
            chunks = chunk_text(content)
            if not chunks:
                continue
            expected_ids = [
                hashlib.md5(f"{doc_id}_{i}_{c}".encode("utf-8")).hexdigest()
                for i, c in enumerate(chunks)
            ]
            from app.knowledge.store import _get_collection
            collection = _get_collection(ACTIVE_COLLECTIONS["news"])
            try:
                existing = collection.get(ids=expected_ids, include=[])
                retrieved = existing.get("ids", []) if existing else []
                if len(retrieved) == len(chunks):
                    found += 1
                else:
                    missing += 1
                    all_ok = False
            except Exception:
                missing += 1
                all_ok = False
        total = found + missing
        status = "PASS" if missing == 0 else "FAIL"
        marker = "✓" if missing == 0 else "✗"
        logger.info(f"  {marker} news:20s 采样{total:>3}条  匹配{found:>3}条  缺失{missing:>2}条  [{status}]")

    # ---------- company_profile ----------
    def check_company_profiles():
        nonlocal all_ok
        stmt = select(CompanyProfile, CompanyMaster.stock_name).join(
            CompanyMaster, CompanyProfile.stock_code == CompanyMaster.stock_code
        )
        rows = db.execute(stmt).all()
        if not rows:
            logger.info("  → company_profile: DB 无数据，跳过")
            return
        samples = random.sample(rows, min(sample_size, len(rows)))
        found = missing = 0
        for profile, stock_name in samples:
            parts = [p for p in [profile.business_summary, profile.market_position, profile.management_summary] if p]
            if not parts:
                continue
            text = "\n".join(parts)
            doc_id = _doc_id("company_profile", profile.id, text)
            chunks = chunk_text(text)
            if not chunks:
                continue
            expected_ids = [
                hashlib.md5(f"{doc_id}_{i}_{c}".encode("utf-8")).hexdigest()
                for i, c in enumerate(chunks)
            ]
            from app.knowledge.store import _get_collection
            collection = _get_collection(ACTIVE_COLLECTIONS["company_profile"])
            try:
                existing = collection.get(ids=expected_ids, include=[])
                retrieved = existing.get("ids", []) if existing else []
                if len(retrieved) == len(chunks):
                    found += 1
                else:
                    missing += 1
                    all_ok = False
            except Exception:
                missing += 1
                all_ok = False
        total = found + missing
        status = "PASS" if missing == 0 else "FAIL"
        marker = "✓" if missing == 0 else "✗"
        logger.info(f"  {marker} company_profile:20s 采样{total:>3}条  匹配{found:>3}条  缺失{missing:>2}条  [{status}]")

    check_announcements()
    check_financial_notes()
    check_news()
    check_company_profiles()

    logger.info(f"  结果: {'通过' if all_ok else '未通过'}")
    return all_ok


# ---------------------------------------------------------------------------
# 4. 集合隔离验证
# ---------------------------------------------------------------------------
def verify_collection_isolation(vs: VectorKnowledgeStore, sample_size: int = 20) -> bool:
    """抽查各集合的 metadata.doc_type，确认没有串库。"""
    logger.info("\n" + "=" * 60)
    logger.info("【4/5】集合隔离验证")
    logger.info("=" * 60)

    all_ok = True

    for doc_type, collection_name in ACTIVE_COLLECTIONS.items():
        from app.knowledge.store import _get_collection

        collection = _get_collection(collection_name)
        total = collection.count()
        if total == 0:
            logger.info(f"  → {doc_type}: 空集合，跳过")
            continue

        n = min(sample_size, total)
        try:
            sample = collection.peek(limit=n)
        except Exception:
            try:
                sample = collection.get(limit=n, include=["metadatas"])
            except Exception as exc:
                logger.warning(f"  → {doc_type}: 获取失败 {exc}")
                continue

        metas = sample.get("metadatas", []) or []
        wrong = sum(1 for m in metas if m.get("doc_type") != doc_type)
        if wrong:
            all_ok = False

        status = "PASS" if wrong == 0 else "FAIL"
        marker = "✓" if wrong == 0 else "✗"
        logger.info(
            f"  {marker} {doc_type:20s} 抽查{n:>3}条  异常{wrong:>2}条  [{status}]"
        )

    logger.info(f"  结果: {'通过' if all_ok else '未通过'}")
    return all_ok


# ---------------------------------------------------------------------------
# 5. 检索闭环验证
# ---------------------------------------------------------------------------
def verify_retrieval_loopback(vs: VectorKnowledgeStore, sample_size: int = 10) -> bool:
    """从 Chroma 中随机取 chunk，用其内容检索，验证能召回自身（top-3 内）。"""
    logger.info("\n" + "=" * 60)
    logger.info("【5/5】检索闭环验证（向量自洽性）")
    logger.info("=" * 60)

    all_ok = True

    for doc_type, collection_name in ACTIVE_COLLECTIONS.items():
        from app.knowledge.store import _get_collection

        collection = _get_collection(collection_name)
        total = collection.count()
        if total == 0:
            logger.info(f"  → {doc_type}: 空集合，跳过")
            continue

        n = min(sample_size, total)
        try:
            sample = collection.peek(limit=n)
        except Exception:
            try:
                sample = collection.get(limit=n, include=["documents", "metadatas"])
            except Exception as exc:
                logger.warning(f"  → {doc_type}: 获取失败 {exc}")
                continue

        docs = sample.get("documents", []) or []
        metas = sample.get("metadatas", []) or []

        hit = 0
        miss = 0
        for doc_text, meta in zip(docs, metas):
            if not doc_text:
                continue
            stock_code = meta.get("stock_code", "")
            filters = {"stock_code": stock_code} if stock_code else None

            try:
                results = vs.search(
                    query=doc_text,
                    top_k=3,
                    doc_types=[doc_type],
                    filters=filters,
                )
            except Exception:
                miss += 1
                all_ok = False
                continue

            # 放宽条件：top-3 内只要文本一致就算命中
            matched = any(r.get("text") == doc_text for r in results)
            if matched:
                hit += 1
            else:
                miss += 1
                all_ok = False

        total_checked = hit + miss
        status = "PASS" if miss == 0 else "FAIL"
        marker = "✓" if miss == 0 else "✗"
        logger.info(
            f"  {marker} {doc_type:20s} 采样{total_checked:>3}条  召回{hit:>3}条  丢失{miss:>2}条  [{status}]"
        )

    logger.info(f"  结果: {'通过' if all_ok else '未通过'}")
    return all_ok


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="向量索引一致性验证工具")
    parser.add_argument("--sample-size", type=int, default=10, help="每类型采样条数（默认 10）")
    args = parser.parse_args()

    db = SessionLocal()
    vs = get_vector_store()

    try:
        results = {}
        results["count"] = verify_counts(db, vs)
        results["metadata"] = verify_metadata(vs, sample_size=args.sample_size * 2)
        results["tracing"] = verify_source_tracing(db, vs, sample_size=args.sample_size)
        results["isolation"] = verify_collection_isolation(vs, sample_size=args.sample_size * 2)
        results["loopback"] = verify_retrieval_loopback(vs, sample_size=args.sample_size)

        logger.info("\n" + "=" * 60)
        logger.info("【最终报告】")
        logger.info("=" * 60)
        logger.info(f"  数量一致性 : {'✓ 通过' if all(results['count'].values()) else '✗ 未通过'}")
        logger.info(f"  Metadata   : {'✓ 通过' if results['metadata'] else '✗ 未通过'}")
        logger.info(f"  内容溯源   : {'✓ 通过' if results['tracing'] else '✗ 未通过'}")
        logger.info(f"  集合隔离   : {'✓ 通过' if results['isolation'] else '✗ 未通过'}")
        logger.info(f"  检索闭环   : {'✓ 通过' if results['loopback'] else '✗ 未通过'}")

        all_pass = (
            all(results["count"].values())
            and results["metadata"]
            and results["tracing"]
            and results["isolation"]
            and results["loopback"]
        )

        if all_pass:
            logger.info("\n🎉 全部验证通过，向量索引状态正常。")
            sys.exit(0)
        else:
            logger.info("\n⚠️ 部分验证未通过，建议检查同步日志或重建索引。")
            sys.exit(1)

    except Exception as exc:
        logger.error(f"验证异常: {exc}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
