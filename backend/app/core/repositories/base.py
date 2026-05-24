from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import Select, and_, delete, select, update
from sqlalchemy.orm import Session


class BaseRepository:
    """Thin wrapper around a SQLAlchemy Session.

    Repositories are responsible only for direct persistence operations
    (CRUD / simple joins / simple filters). Business composition belongs
    in service layer.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, entity: Any, *, flush: bool = True) -> Any:
        self.db.add(entity)
        if flush:
            self.db.flush()
        return entity

    def add_all(self, entities: Iterable[Any], *, flush: bool = True) -> list[Any]:
        items = list(entities)
        self.db.add_all(items)
        if flush:
            self.db.flush()
        return items

    def delete(self, entity: Any, *, flush: bool = True) -> None:
        self.db.delete(entity)
        if flush:
            self.db.flush()

    def delete_where(self, model: Any, /, **filters: Any) -> int:
        stmt = delete(model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(model, key) == value)
        result = self.db.execute(stmt)
        self.db.flush()
        return int(result.rowcount or 0)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, entity: Any) -> None:
        self.db.refresh(entity)

    def scalar_one_or_none(self, stmt: Select[Any]) -> Any | None:
        return self.db.execute(stmt).scalar_one_or_none()

    def scalars_all(self, stmt: Select[Any]) -> list[Any]:
        return list(self.db.execute(stmt).scalars().all())

    def scalar_first(self, stmt: Select[Any]) -> Any | None:
        return self.db.execute(stmt).scalars().first()

    def get_one_by(self, model: Any, /, **filters: Any) -> Any | None:
        stmt = select(model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(model, key) == value)
        return self.scalar_one_or_none(stmt)

    def list_by(self, model: Any, /, *, order_by: Sequence[Any] | None = None, limit: int | None = None, **filters: Any) -> list[Any]:
        stmt = select(model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(model, key) == value)
        if order_by:
            for col in order_by:
                stmt = stmt.order_by(col)
        if limit:
            stmt = stmt.limit(limit)
        return self.scalars_all(stmt)

    def upsert(self, model: Any, *, unique_fields: dict[str, Any], values: dict[str, Any]) -> tuple[Any, bool]:
        entity = self.get_one_by(model, **unique_fields)
        created = entity is None
        if entity is None:
            entity = model(**{**unique_fields, **values})
            self.add(entity)
        else:
            for key, value in values.items():
                setattr(entity, key, value)
            self.db.flush()
        return entity, created

    def bulk_upsert(
        self,
        model: Any,
        *,
        items: list[dict[str, Any]],
        unique_keys: Sequence[str],
        mutable_fields: Sequence[str] | None = None,
    ) -> tuple[list[Any], int, int]:
        entities: list[Any] = []
        created_count = 0
        updated_count = 0
        mutable_set = set(mutable_fields) if mutable_fields is not None else None

        for item in items:
            unique_fields = {key: item.get(key) for key in unique_keys}
            values = {k: v for k, v in item.items() if k not in unique_keys and k != "id"}
            if mutable_set is not None:
                values = {k: v for k, v in values.items() if k in mutable_set}
            entity, created = self.upsert(model, unique_fields=unique_fields, values=values)
            entities.append(entity)
            if created:
                created_count += 1
            else:
                updated_count += 1
        return entities, created_count, updated_count

    @staticmethod
    def paginate(stmt: Select[Any], *, limit: int | None = None, offset: int | None = None) -> Select[Any]:
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        return stmt

    @staticmethod
    def order_latest(stmt: Select[Any], *columns: Any) -> Select[Any]:
        for col in columns:
            stmt = stmt.order_by(col.desc())
        return stmt

    @staticmethod
    def stmt(model: Any) -> Select[Any]:
        return select(model)

    # ------------------------------------------------------------------
    # 热冷库查询 + query_count 自增
    # ------------------------------------------------------------------

    # 热库结果少于此值时才查冷库补充
    COLD_FALLBACK_THRESHOLD = 5

    def _hot_cold_list(
        self,
        hot_stmt: Select[Any],
        cold_stmt: Select[Any],
        *,
        limit: int | None = None,
    ) -> list[Any]:
        """热库优先查询，结果不足 COLD_FALLBACK_THRESHOLD 时从冷库补充。"""
        hot_rows = self.scalars_all(hot_stmt)
        if len(hot_rows) < self.COLD_FALLBACK_THRESHOLD:
            needed = (limit or self.COLD_FALLBACK_THRESHOLD) - len(hot_rows)
            if needed > 0:
                cold_rows = self.scalars_all(cold_stmt.limit(needed))
                all_rows = hot_rows + cold_rows
            else:
                all_rows = hot_rows
        else:
            all_rows = hot_rows[:limit] if limit else hot_rows
        self._increment_query_count(all_rows)
        return all_rows

    def _hot_cold_get(self, hot_model: Any, cold_model: Any, record_id: int) -> Any | None:
        """按 id 查单条：先热库，没有再查冷库。"""
        row = self.scalar_one_or_none(select(hot_model).where(hot_model.id == record_id))
        if row is None:
            row = self.scalar_one_or_none(select(cold_model).where(cold_model.id == record_id))
        if row is not None:
            self._increment_query_count([row])
        return row

    def _increment_query_count(self, rows: list[Any]) -> None:
        """批量自增 query_count，按模型分组执行 UPDATE。"""
        if not rows:
            return
        groups: dict[type, list[int]] = {}
        for row in rows:
            if hasattr(row, "query_count") and hasattr(row, "id"):
                groups.setdefault(type(row), []).append(row.id)
        for model, ids in groups.items():
            try:
                self.db.execute(
                    update(model).where(model.id.in_(ids)).values(query_count=model.query_count + 1)
                )
            except Exception:
                pass
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
