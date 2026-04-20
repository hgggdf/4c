from __future__ import annotations

from service.base import BaseService
from service.guards import require_non_empty, require_positive_int
from service.requests import RebuildEmbeddingsRequest, SearchRequest
from service.serializers import normalize_value


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
    }

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

        return {
            "query": query,
            "resolved_stock_code": filters.get("stock_code"),
            "top_k": top_k,
            "doc_types": doc_types,
            "items": self._normalize_hits(hits),
        }

    def _rebuild_document_embeddings(self, req: RebuildEmbeddingsRequest):
        doc_type = require_non_empty(req.doc_type, "doc_type")
        if not req.source_ids:
            raise ValueError("source_ids is required")

        try:
            from knowledge import sync as kg_sync
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