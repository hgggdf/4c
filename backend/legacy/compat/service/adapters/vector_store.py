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
    面向 knowledge.store 的适配器。
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
        try:
            from knowledge.store import get_store, get_vector_store
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
            else:
                # TF-IDF fallback 先多取一些结果，再在本地做 metadata 过滤
                fallback_top_k = max(top_k * 5, top_k)
                hits = get_store().search(query, top_k=fallback_top_k)
        except Exception:
            hits = []

        if not filters:
            return hits

        def _match(meta: dict | None) -> bool:
            if not meta:
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

        filtered = [h for h in hits if _match(h.get("metadata") or h.get("meta"))]
        return filtered[:top_k]

    def count(self, *, doc_type: str | None = None) -> int:
        try:
            from knowledge.store import get_vector_store
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
            from knowledge.store import get_vector_store
        except Exception:
            return 0

        try:
            return get_vector_store().delete_by_source(
                doc_type=doc_type,
                source_table=source_table,
                source_pks=[str(x) for x in source_pks],
            )
        except Exception:
            return 0