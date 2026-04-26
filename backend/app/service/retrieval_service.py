from __future__ import annotations

from sqlalchemy import or_, select

from app.core.database.models.announcement_hot import AnnouncementRawHot
from app.core.database.models.company import CompanyMaster, CompanyProfile
from app.core.database.models.news_hot import NewsHot, NewsRawHot
from app.core.database.models.research_report_hot import ResearchReportHot

from .base import BaseService
from .guards import require_non_empty, require_positive_int
from .requests import RebuildEmbeddingsRequest, SearchRequest
from .serializers import model_to_dict, normalize_value


class RetrievalService(BaseService):
    def __init__(self, *, ctx, company_service=None) -> None:
        super().__init__(ctx=ctx)
        self.company_service = company_service

    DOC_TYPE_TO_FILTER = {
        "announcement": {"doc_type": "announcement"},
        "financial_note": {"doc_type": "financial_note"},
        "news": {"doc_type": "news"},
        "report": {"doc_type": "report"},
        "policy": {"doc_type": "policy"},
        "company_profile": {"doc_type": "company_profile"},
    }

    DOC_TYPE_TO_TABLE = {
        "announcement": "announcement_raw_hot",
        "financial_note": "financial_notes_hot",
        "news": "news_raw_hot",
        "company_profile": "company_profile",
        "report": "research_report_hot",
    }

    ANNOUNCEMENT_SOURCE_FIELDS = (
        "id",
        "stock_code",
        "title",
        "publish_date",
        "announcement_type",
        "exchange",
        "content",
        "source_url",
        "source_type",
        "file_hash",
        "created_at",
    )

    FINANCIAL_NOTE_SOURCE_FIELDS = (
        "id",
        "stock_code",
        "report_date",
        "note_type",
        "note_json",
        "note_text",
        "source_type",
        "source_url",
        "created_at",
    )

    NEWS_SOURCE_FIELDS = (
        "id",
        "news_uid",
        "title",
        "publish_time",
        "source_name",
        "source_url",
        "author_name",
        "content",
        "news_type",
        "language",
        "file_hash",
        "created_at",
    )

    COMPANY_PROFILE_SOURCE_FIELDS = (
        "id",
        "stock_code",
        "business_summary",
        "core_products_json",
        "main_segments_json",
        "market_position",
        "management_summary",
        "updated_at",
    )

    RESEARCH_REPORT_SOURCE_FIELDS = (
        "id",
        "report_uid",
        "scope_type",
        "stock_code",
        "industry_code",
        "title",
        "publish_date",
        "report_org",
        "content",
        "summary_text",
        "source_type",
        "source_url",
        "created_at",
    )

    def search_announcements(self, req: SearchRequest):
        return self._run(lambda: self._search(req, doc_type="announcement"), trace_id=req.trace_id)

    def search_financial_notes(self, req: SearchRequest):
        return self._run(lambda: self._search(req, doc_type="financial_note"), trace_id=req.trace_id)

    def search_news(self, req: SearchRequest):
        return self._run(lambda: self._search(req, doc_type="news"), trace_id=req.trace_id)

    def search_reports(self, req: SearchRequest):
        return self._run(lambda: self._search(req, doc_type="report"), trace_id=req.trace_id)

    def search_policies(self, req: SearchRequest):
        return self._run(lambda: self._search(req, doc_type="policy"), trace_id=req.trace_id)

    def search_text_evidence(self, req: SearchRequest):
        return self._run(lambda: self._search(req, doc_type=None), trace_id=req.trace_id)

    def search_hybrid(self, req: SearchRequest):
        return self._run(lambda: self._search_hybrid(req), trace_id=req.trace_id)

    def search_announcement_evidence(self, req: SearchRequest):
        return self.search_announcements(req)

    def search_financial_note_evidence(self, req: SearchRequest):
        return self.search_financial_notes(req)

    def search_news_evidence(self, req: SearchRequest):
        return self.search_news(req)

    def rebuild_document_embeddings(self, req: RebuildEmbeddingsRequest):
        return self._run(lambda: self._rebuild_document_embeddings(req), trace_id=req.trace_id)

    def delete_document_embeddings(self, req: RebuildEmbeddingsRequest):
        return self._run(lambda: self._delete_document_embeddings(req), trace_id=req.trace_id)

    def _resolve_stock_code(self, req: SearchRequest) -> str | None:
        """
        优先使用显式 stock_code；
        否则从 query 中用 CompanyService 解析。
        """
        if req.stock_code:
            return req.stock_code

        if not self.company_service:
            return None

        resolved = self.company_service.resolve_company(req.query)
        if not resolved.success or not resolved.data:
            return None

        first = resolved.data[0]
        if isinstance(first, dict):
            return first.get("stock_code")
        return getattr(first, "stock_code", None)

    def _build_filters(self, req: SearchRequest, *, doc_type: str | None) -> dict:
        filters: dict = {}
        if doc_type:
            filters.update(self.DOC_TYPE_TO_FILTER.get(doc_type, {"doc_type": doc_type}))

        stock_code = self._resolve_stock_code(req)
        if stock_code:
            filters["stock_code"] = stock_code

        if req.industry_code:
            filters["industry_code"] = req.industry_code

        return filters

    def _normalize_hits(self, hits: list[dict]) -> list[dict]:
        items = []
        for hit in hits:
            meta = hit.get("metadata") or hit.get("meta") or {}
            items.append(
                {
                    "chunk_id": hit.get("chunk_id") or hit.get("id"),
                    "doc_id": hit.get("doc_id") or meta.get("doc_id"),
                    "text": hit.get("text") or hit.get("document") or "",
                    "score": normalize_value(hit.get("score") if hit.get("score") is not None else hit.get("distance")),
                    "metadata": normalize_value(meta),
                }
            )
        return items

    def _search(self, req: SearchRequest, *, doc_type: str | None):
        query = require_non_empty(req.query, "query")
        top_k = require_positive_int(req.top_k, "top_k")
        filters = self._build_filters(req, doc_type=doc_type)

        doc_types = [doc_type] if doc_type else req.doc_types

        hits = self.ctx.vector_store.search(
            query=query,
            top_k=top_k,
            filters=filters or None,
            doc_types=doc_types,
        )

        items = self._normalize_hits(hits)
        hydrated_items = self._hydrate_items(items)

        return {
            "query": query,
            "resolved_stock_code": filters.get("stock_code"),
            "top_k": top_k,
            "doc_types": doc_types,
            "items": hydrated_items,
        }

    def _search_hybrid(self, req: SearchRequest):
        query = require_non_empty(req.query, "query")
        top_k = require_positive_int(req.top_k, "top_k")
        filters = self._build_filters(req, doc_type=None)

        keyword_items = self._keyword_search(query=query, top_k=top_k, filters=filters, doc_types=req.doc_types)
        vector_items = self._search(req, doc_type=None)["items"]

        merged = self._merge_hybrid_results(keyword_items, vector_items, top_k=top_k)
        return {
            "query": query,
            "resolved_stock_code": filters.get("stock_code"),
            "top_k": top_k,
            "doc_types": req.doc_types,
            "items": merged,
            "keyword_count": len(keyword_items),
            "vector_count": len(vector_items),
        }

    def _keyword_search(self, *, query: str, top_k: int, filters: dict, doc_types: list[str] | None) -> list[dict]:
        normalized_query = query.strip()
        stock_code = filters.get("stock_code")
        industry_code = filters.get("industry_code")
        lowered_query = normalized_query.lower()

        def _run(db):
            items: list[dict] = []

            def push_rows(rows, doc_type: str, source_pk_field: str, title_field: str = "title", text_field: str = "content"):
                for row in rows:
                    source_pk = getattr(row, source_pk_field, None)
                    title = getattr(row, title_field, None) or ""
                    text = getattr(row, text_field, None) or ""
                    haystack = f"{title} {text}".lower()
                    score = 0.0
                    if normalized_query and normalized_query in title:
                        score += 2.5
                    if lowered_query and lowered_query in haystack:
                        score += 1.8
                    if stock_code and getattr(row, "stock_code", None) == stock_code:
                        score += 1.0
                    if industry_code and getattr(row, "industry_code", None) == industry_code:
                        score += 0.8
                    if score <= 0:
                        continue
                    items.append({
                        "doc_type": doc_type,
                        "doc_id": source_pk,
                        "chunk_id": source_pk,
                        "text": text[:1000],
                        "score": round(score, 4),
                        "metadata": {
                            "doc_type": doc_type,
                            "source_pk": str(source_pk) if source_pk is not None else None,
                            "title": title,
                        },
                    })

            if doc_types is None or "announcement" in doc_types:
                rows = db.execute(
                    select(AnnouncementRawHot)
                    .where(
                        or_(
                            AnnouncementRawHot.title.contains(normalized_query),
                            AnnouncementRawHot.content.contains(normalized_query),
                            AnnouncementRawHot.summary_text.contains(normalized_query),
                        )
                    )
                    .order_by(AnnouncementRawHot.publish_date.desc(), AnnouncementRawHot.created_at.desc())
                    .limit(top_k * 3)
                ).scalars().all()
                push_rows(rows, "announcement", "id", title_field="title", text_field="content")

            if doc_types is None or "news" in doc_types:
                rows = db.execute(
                    select(NewsRawHot)
                    .where(
                        or_(
                            NewsRawHot.title.contains(normalized_query),
                            NewsRawHot.content.contains(normalized_query),
                            NewsRawHot.summary_text.contains(normalized_query),
                        )
                    )
                    .order_by(NewsRawHot.publish_time.desc(), NewsRawHot.created_at.desc())
                    .limit(top_k * 3)
                ).scalars().all()
                push_rows(rows, "news", "id", title_field="title", text_field="content")

            if doc_types is None or "report" in doc_types:
                rows = db.execute(
                    select(ResearchReportHot)
                    .where(
                        or_(
                            ResearchReportHot.title.contains(normalized_query),
                            ResearchReportHot.content.contains(normalized_query),
                            ResearchReportHot.summary_text.contains(normalized_query),
                        )
                    )
                    .order_by(ResearchReportHot.publish_date.desc(), ResearchReportHot.created_at.desc())
                    .limit(top_k * 3)
                ).scalars().all()
                push_rows(rows, "report", "id", title_field="title", text_field="content")

            if doc_types is None or "company_profile" in doc_types:
                rows = db.execute(
                    select(CompanyProfile, CompanyMaster.stock_name)
                    .join(CompanyMaster, CompanyMaster.stock_code == CompanyProfile.stock_code)
                    .where(
                        or_(
                            CompanyMaster.stock_name.contains(normalized_query),
                            CompanyMaster.full_name.contains(normalized_query),
                            CompanyProfile.business_summary.contains(normalized_query),
                        )
                    )
                    .limit(top_k * 3)
                ).all()
                for profile, stock_name in rows:
                    score = 2.0
                    if stock_name and normalized_query in stock_name:
                        score += 1.0
                    items.append({
                        "doc_type": "company_profile",
                        "doc_id": profile.id,
                        "chunk_id": profile.id,
                        "text": profile.business_summary or "",
                        "score": round(score, 4),
                        "metadata": {
                            "doc_type": "company_profile",
                            "source_pk": str(profile.id),
                            "stock_name": stock_name,
                            "title": stock_name,
                        },
                    })

            items.sort(key=lambda item: item["score"], reverse=True)
            return self._hydrate_items(items[:top_k])

        return self._with_db(_run)

    def _merge_hybrid_results(self, keyword_items: list[dict], vector_items: list[dict], top_k: int) -> list[dict]:
        merged: dict[tuple[str | None, str | None], dict] = {}

        def add_item(item: dict, source: str):
            metadata = dict(item.get("metadata") or {})
            doc_type = metadata.get("doc_type") or item.get("doc_type")
            source_pk = metadata.get("source_pk") or item.get("doc_id") or item.get("chunk_id")
            key = (str(doc_type) if doc_type is not None else None, str(source_pk) if source_pk is not None else None)
            current = merged.get(key)
            payload = dict(item)
            payload["match_source"] = source
            payload["keyword_score"] = item.get("score") if source == "keyword" else None
            payload["vector_score"] = item.get("score") if source == "vector" else None
            payload["final_score"] = float(item.get("score") or 0)
            if current is None or payload["final_score"] > current["final_score"]:
                merged[key] = payload
            elif current is not None:
                current["match_source"] = "hybrid"
                current["keyword_score"] = current.get("keyword_score") or payload.get("keyword_score")
                current["vector_score"] = current.get("vector_score") or payload.get("vector_score")
                current["final_score"] = max(current["final_score"], payload["final_score"])

        for item in keyword_items:
            add_item(item, "keyword")
        for item in vector_items:
            add_item(item, "vector")

        results = list(merged.values())
        results.sort(key=lambda item: item.get("final_score", 0), reverse=True)
        return results[:top_k]

    def _hydrate_items(self, items: list[dict]) -> list[dict]:
        if not items:
            return items

        return self._with_db(lambda db: self._hydrate_items_with_db(db, items))

    def _hydrate_items_with_db(self, db, items: list[dict]) -> list[dict]:
        cache: dict[tuple[str, str], dict | None] = {}
        hydrated_items: list[dict] = []

        for item in items:
            metadata = dict(item.get("metadata") or {})
            doc_type = str(metadata.get("doc_type") or "")
            source_pk = str(metadata.get("source_pk") or "")
            key = (doc_type, source_pk)

            source_record = None
            if doc_type and source_pk:
                if key not in cache:
                    cache[key] = self._load_source_record(db, doc_type=doc_type, source_pk=source_pk)
                source_record = cache[key]

            hydrated_item = dict(item)
            hydrated_item["metadata"] = metadata
            hydrated_item["source_found"] = source_record is not None
            hydrated_item["source_record"] = normalize_value(source_record)
            hydrated_items.append(hydrated_item)

        return hydrated_items

    def _load_source_record(self, db, *, doc_type: str, source_pk: str) -> dict | None:
        try:
            source_id = int(source_pk)
        except (TypeError, ValueError):
            return None

        if doc_type == "announcement":
            from app.core.repositories.announcement_repository import AnnouncementRepository

            entity = AnnouncementRepository(db).get_raw_by_id(source_id)
            if not entity:
                return None
            return model_to_dict(entity, self.ANNOUNCEMENT_SOURCE_FIELDS)

        if doc_type == "financial_note":
            from app.core.repositories.financial_repository import FinancialRepository

            entity = FinancialRepository(db).get_financial_note_by_id(source_id)
            if not entity:
                return None
            return model_to_dict(entity, self.FINANCIAL_NOTE_SOURCE_FIELDS)

        if doc_type == "news":
            from app.core.repositories.news_repository import NewsRepository

            entity = NewsRepository(db).get_news_raw_by_id(source_id)
            if not entity:
                return None
            return model_to_dict(entity, self.NEWS_SOURCE_FIELDS)

        if doc_type == "company_profile":
            from app.core.database.models.company import CompanyMaster, CompanyProfile

            row = db.execute(
                select(CompanyProfile, CompanyMaster.stock_name)
                .outerjoin(CompanyMaster, CompanyProfile.stock_code == CompanyMaster.stock_code)
                .where(CompanyProfile.id == source_id)
            ).first()
            if not row:
                return None

            profile, stock_name = row
            payload = model_to_dict(profile, self.COMPANY_PROFILE_SOURCE_FIELDS)
            payload["stock_name"] = normalize_value(stock_name)
            return payload

        if doc_type == "report":
            from app.core.database.models.research_report_hot import ResearchReportHot

            entity = db.execute(
                select(ResearchReportHot).where(ResearchReportHot.id == source_id)
            ).scalars().first()
            if not entity:
                return None
            return model_to_dict(entity, self.RESEARCH_REPORT_SOURCE_FIELDS)

        return None

    def _rebuild_document_embeddings(self, req: RebuildEmbeddingsRequest):
        doc_type = require_non_empty(req.doc_type, "doc_type")
        if not req.source_ids:
            raise ValueError("source_ids is required")

        try:
            from app.knowledge import sync as kg_sync
        except Exception:
            return {
                "doc_type": doc_type,
                "source_ids": req.source_ids,
                "status": "knowledge_sync_unavailable",
            }

        def _run_sync(db):
            if doc_type == "announcement":
                return kg_sync.sync_announcements_by_ids(db, req.source_ids, is_hot=True)
            if doc_type == "financial_note":
                return kg_sync.sync_financial_notes_by_ids(db, req.source_ids, is_hot=True)
            if doc_type == "company_profile":
                return kg_sync.sync_company_profiles_by_ids(db, req.source_ids)
            if doc_type == "news":
                return kg_sync.sync_news_by_ids(db, req.source_ids, is_hot=True)
            return 0

        count = self._with_db(_run_sync)
        return {
            "doc_type": doc_type,
            "source_ids": req.source_ids,
            "reindexed_chunks": count,
        }

    def _delete_document_embeddings(self, req: RebuildEmbeddingsRequest):
        doc_type = require_non_empty(req.doc_type, "doc_type")
        if not req.source_ids:
            raise ValueError("source_ids is required")

        source_table = self.DOC_TYPE_TO_TABLE.get(doc_type)
        if not source_table:
            return {
                "doc_type": doc_type,
                "source_ids": req.source_ids,
                "deleted_chunks": 0,
                "status": "unsupported_doc_type",
            }

        deleted = self.ctx.vector_store.delete_by_source(
            doc_type=doc_type,
            source_table=source_table,
            source_pks=req.source_ids,
        )
        return {
            "doc_type": doc_type,
            "source_ids": req.source_ids,
            "deleted_chunks": deleted,
        }