"""数据库统计仓储，用于读取各类缓存表的规模信息。"""

from sqlalchemy import text
from sqlalchemy.orm import Session


class DatabaseStatsRepository:
    """负责聚合数据库中的统计指标。"""

    def ping(self, db: Session) -> int:
        """执行最小 SQL 语句验证数据库连接可用。"""
        return int(db.execute(text("SELECT 1")).scalar() or 0)

    def list_stock_daily_stats(self, db: Session) -> list[dict]:
        """读取 stock_daily 表中每只股票的记录量和日期范围。"""
        result = db.execute(
            text(
                """
                SELECT
                    stock_code,
                    COUNT(*) AS record_count,
                    MIN(trade_date) AS earliest_date,
                    MAX(trade_date) AS latest_date
                FROM stock_daily
                GROUP BY stock_code
                ORDER BY stock_code
                """
            )
        )
        return [
            {
                "stock_code": row.stock_code,
                "record_count": int(row.record_count or 0),
                "earliest_date": str(row.earliest_date),
                "latest_date": str(row.latest_date),
            }
            for row in result.fetchall()
        ]

    def get_table_counts(self, db: Session, table_names: list[str]) -> dict[str, int]:
        """批量统计指定数据表的记录数。"""
        counts: dict[str, int] = {}
        for table_name in table_names:
            counts[table_name] = int(
                db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar() or 0
            )
        return counts