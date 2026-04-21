from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from .adapters.cache import CacheAdapter, InMemoryTTLCacheAdapter
from .adapters.vector_store import KnowledgeVectorStoreAdapter, VectorStoreAdapter

SessionFactory = Callable[[], Any]


@dataclass(slots=True)
class ServiceContext:
    session_factory: SessionFactory
    cache: CacheAdapter
    vector_store: VectorStoreAdapter

    @contextmanager
    def session(self) -> Generator[Any, None, None]:
        db = self.session_factory()
        try:
            yield db
            try:
                db.commit()
            except Exception:
                pass
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                db.close()
            except Exception:
                pass


def build_default_context(*, session_factory: SessionFactory | None = None) -> ServiceContext:
    if session_factory is None:
        from app.core.database.session import SessionLocal
        session_factory = SessionLocal
    return ServiceContext(
        session_factory=session_factory,
        cache=InMemoryTTLCacheAdapter(),
        vector_store=KnowledgeVectorStoreAdapter(),
    )
