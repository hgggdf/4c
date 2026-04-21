from __future__ import annotations

from typing import Any, Protocol


class VectorStoreAdapter(Protocol):
    def search(
        self,
        query: str,
        *,
        top_k: int,
        filters: dict[str, Any] | None = None,
        doc_types: list[str] | None = None,
    ) -> list[dict]: ...

    def count(self, *, doc_type: str | None = None) -> int: ...

    def delete_by_source(
        self,
        *,
        doc_type: str,
        source_table: str,
        source_pks: list[int | str],
    ) -> int: ...


class KnowledgeVectorStoreAdapter:
    """
    面向 app.knowledge.store 的适配器。
    service 层只依赖这个适配器，不直接依赖 Chroma / TF-IDF 实现。
    """

    def search(
        self,
        query: str,
        *,
        top_k: int,
        filters: dict[str, Any] | None = None,
        doc_types: list[str] | None = None,
    ) -> list[dict]:
        typed_retrieval = bool(filters or doc_types)

        try:
            from app.knowledge.store import get_store, get_vector_store
        except Exception:
            return []

        filters = dict(filters or {})

        try:
            vs = get_vector_store()
            if vs.count() > 0:
                hits = vs.search(
                    query=query,
                    top_k=top_k,
                    doc_types=doc_types,
                    filters=filters or None,
                )
            elif typed_retrieval:
                hits = []
            else:
                hits = get_store().search(
                    query,
                    top_k=max(top_k * 3, top_k),
                    filters=filters or None,
                    doc_types=doc_types,
                )
        except Exception:
            if typed_retrieval:
                hits = []
            else:
                try:
                    hits = get_store().search(
                        query,
                        top_k=max(top_k * 3, top_k),
                        filters=filters or None,
                        doc_types=doc_types,
                    )
                except Exception:
                    hits = []

        if not filters and not doc_types:
            return hits[:top_k]

        def _match(meta: dict | None) -> bool:
            meta = meta or {}
            if doc_types and meta.get("doc_type") not in set(doc_types):
                return False
            for key, expected in filters.items():
                if expected is None:
                    continue
                actual = meta.get(key)
                if isinstance(expected, (list, tuple, set)):
                    if actual not in expected:
                        return False
                elif actual != expected:
                    return False
            return True

        return [h for h in hits if _match(h.get("metadata") or h.get("meta"))][:top_k]

    def count(self, *, doc_type: str | None = None) -> int:
        try:
            from app.knowledge.store import get_vector_store
        except Exception:
            return 0

        try:
            return get_vector_store().count(doc_type=doc_type)
        except Exception:
            return 0

    def delete_by_source(
        self,
        *,
        doc_type: str,
        source_table: str,
        source_pks: list[int | str],
    ) -> int:
        try:
            from app.knowledge.store import get_store, get_vector_store
        except Exception:
            return 0

        deleted = 0
        try:
            deleted += get_vector_store().delete_by_source(
                doc_type=doc_type,
                source_table=source_table,
                source_pks=[str(x) for x in source_pks],
            )
        except Exception:
            pass

        try:
            deleted += get_store().delete_by_source(
                source_table=source_table,
                source_pks=[str(x) for x in source_pks],
            )
        except Exception:
            pass

        return deleted
