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

    中文说明：
    - Repository 层只负责“怎么查表、怎么写表”，不承载业务流程编排。
    - Service 层负责参数校验、跨表组合、事务边界和返回结构。
    - 本基类提供通用 CRUD、按唯一键 upsert、冷热库补查和 query_count 维护。
    """

    def __init__(self, db: Session) -> None:
        """保存请求级或任务级 SQLAlchemy Session。"""
        self.db = db

    def add(self, entity: Any, *, flush: bool = True) -> Any:
        """新增单个 ORM 实体；默认 flush 以便马上拿到数据库生成的主键。"""
        self.db.add(entity)
        if flush:
            self.db.flush()
        return entity

    def add_all(self, entities: Iterable[Any], *, flush: bool = True) -> list[Any]:
        """批量新增 ORM 实体；调用方仍负责最终 commit/rollback。"""
        items = list(entities)
        self.db.add_all(items)
        if flush:
            self.db.flush()
        return items

    def delete(self, entity: Any, *, flush: bool = True) -> None:
        """删除单个 ORM 实体。"""
        self.db.delete(entity)
        if flush:
            self.db.flush()

    def delete_where(self, model: Any, /, **filters: Any) -> int:
        """按简单等值条件删除记录，返回数据库报告的删除行数。"""
        stmt = delete(model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(model, key) == value)
        result = self.db.execute(stmt)
        self.db.flush()
        return int(result.rowcount or 0)

    def commit(self) -> None:
        """提交当前 Session 中的所有变更。"""
        self.db.commit()

    def rollback(self) -> None:
        """回滚当前 Session 中尚未提交的变更。"""
        self.db.rollback()

    def refresh(self, entity: Any) -> None:
        """从数据库重新加载实体字段。"""
        self.db.refresh(entity)

    def scalar_one_or_none(self, stmt: Select[Any]) -> Any | None:
        """执行查询并要求最多一条结果；常用于唯一键查询。"""
        return self.db.execute(stmt).scalar_one_or_none()

    def scalars_all(self, stmt: Select[Any]) -> list[Any]:
        """执行查询并返回 ORM 实体列表。"""
        return list(self.db.execute(stmt).scalars().all())

    def scalar_first(self, stmt: Select[Any]) -> Any | None:
        """执行查询并返回第一条 ORM 实体；不强制唯一。"""
        return self.db.execute(stmt).scalars().first()

    def get_one_by(self, model: Any, /, **filters: Any) -> Any | None:
        """按模型字段等值过滤获取单条记录。"""
        stmt = select(model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(model, key) == value)
        return self.scalar_one_or_none(stmt)

    def list_by(self, model: Any, /, *, order_by: Sequence[Any] | None = None, limit: int | None = None, **filters: Any) -> list[Any]:
        """按模型字段等值过滤获取列表，可附加排序和 limit。"""
        stmt = select(model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(model, key) == value)
        if order_by:
            for col in order_by:
                stmt = stmt.order_by(col)
        if limit:
            stmt = stmt.limit(limit)
        return self.scalars_all(stmt)

    def upsert(
        self,
        model: Any,
        *,
        unique_fields: dict[str, Any],
        values: dict[str, Any],
        preserve_on_update: Sequence[str] | None = None,
    ) -> tuple[Any, bool]:
        """按唯一字段实现“存在则更新，不存在则新增”。

        注意：这是应用层先查再写，不是 MySQL 原子 ON DUPLICATE KEY UPDATE。
        并发导入同一唯一键时仍可能撞唯一约束，调用方需要捕获异常或改用原子 upsert。
        """
        entity = self.get_one_by(model, **unique_fields)
        created = entity is None
        if entity is None:
            entity = model(**{**unique_fields, **values})
            self.add(entity)
        else:
            preserved = set(preserve_on_update or [])
            for key, value in values.items():
                if key in preserved:
                    continue
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
        preserve_on_update: Sequence[str] | None = None,
    ) -> tuple[list[Any], int, int]:
        """批量 upsert。

        unique_keys 决定去重口径；mutable_fields 可限制更新字段，避免覆盖不应修改的列。
        返回实体列表、创建数量、更新数量。
        """
        entities: list[Any] = []
        created_count = 0
        updated_count = 0
        mutable_set = set(mutable_fields) if mutable_fields is not None else None

        for item in items:
            unique_fields = {key: item.get(key) for key in unique_keys}
            values = {k: v for k, v in item.items() if k not in unique_keys and k != "id"}
            if mutable_set is not None:
                values = {k: v for k, v in values.items() if k in mutable_set}
            entity, created = self.upsert(
                model,
                unique_fields=unique_fields,
                values=values,
                preserve_on_update=preserve_on_update,
            )
            entities.append(entity)
            if created:
                created_count += 1
            else:
                updated_count += 1
        return entities, created_count, updated_count

    @staticmethod
    def paginate(stmt: Select[Any], *, limit: int | None = None, offset: int | None = None) -> Select[Any]:
        """给查询附加分页参数。"""
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        return stmt

    @staticmethod
    def order_latest(stmt: Select[Any], *columns: Any) -> Select[Any]:
        """按传入字段倒序排序，常用于最新记录优先。"""
        for col in columns:
            stmt = stmt.order_by(col.desc())
        return stmt

    @staticmethod
    def stmt(model: Any) -> Select[Any]:
        """创建模型基础 select 语句，便于子类继续拼条件。"""
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
        # 先查热库；热库结果太少时，再查冷库补齐，避免常规查询直接扫历史大表。
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
        # 单条详情先按热库主键查，未命中再用同 id 查冷库。
        row = self.scalar_one_or_none(select(hot_model).where(hot_model.id == record_id))
        if row is None:
            row = self.scalar_one_or_none(select(cold_model).where(cold_model.id == record_id))
        if row is not None:
            self._increment_query_count([row])
        return row

    def _increment_query_count(self, rows: list[Any]) -> None:
        """批量自增 query_count，按模型分组执行 UPDATE。"""
        # 查询热度用于冷热分层；没有 query_count/id 的模型会被自动跳过。
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
