"""SQLAlchemy 声明式基类定义。"""

from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import DeclarativeBase


# 在 SQLite 测试环境下退回 INTEGER，保证自增主键可用；
# 在 MySQL / PostgreSQL 等正式环境下使用 BIGINT，对齐设计文档。
BIGINT_PK = BigInteger().with_variant(Integer, "sqlite")
BIGINT_FK = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    """所有 ORM 模型共享的声明式基类。"""

    pass
