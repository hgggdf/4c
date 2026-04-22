from __future__ import annotations

import json
from pathlib import Path
import sys

from sqlalchemy import text


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database.session import SessionLocal


QUERIES = {
    "announcement_count": "SELECT COUNT(*) AS c FROM announcement_raw_hot WHERE stock_code='600276' AND created_at >= NOW() - INTERVAL 15 MINUTE",
    "announcement_rows": "SELECT stock_code, title, publish_date, exchange, source_url FROM announcement_raw_hot WHERE stock_code='600276' ORDER BY created_at DESC LIMIT 2",
    "income_count": "SELECT COUNT(*) AS c FROM income_statement_hot WHERE stock_code='600276' AND created_at >= NOW() - INTERVAL 15 MINUTE",
    "metric_count": "SELECT COUNT(*) AS c FROM financial_metric_hot WHERE stock_code='600276' AND created_at >= NOW() - INTERVAL 15 MINUTE",
    "segment_count": "SELECT COUNT(*) AS c FROM business_segment_hot WHERE stock_code='600276' AND created_at >= NOW() - INTERVAL 15 MINUTE",
    "metric_rows": "SELECT stock_code, report_date, metric_name, metric_value FROM financial_metric_hot WHERE stock_code='600276' ORDER BY created_at DESC LIMIT 5",
    "news_count": "SELECT COUNT(*) AS c FROM news_raw_hot WHERE source_name='东方财富研报' AND created_at >= NOW() - INTERVAL 15 MINUTE",
    "news_rows": "SELECT title, news_type, source_name, source_url FROM news_raw_hot WHERE source_name='东方财富研报' ORDER BY created_at DESC LIMIT 4",
    "macro_count": "SELECT COUNT(*) AS c FROM macro_indicator_hot WHERE created_at >= NOW() - INTERVAL 15 MINUTE",
    "macro_rows": "SELECT indicator_name, period, value, source_url FROM macro_indicator_hot ORDER BY created_at DESC LIMIT 6",
}


def main() -> None:
    output: dict[str, object] = {}
    db = SessionLocal()
    try:
        for key, sql in QUERIES.items():
            rows = db.execute(text(sql)).mappings().all()
            if rows and "c" in rows[0] and len(rows[0]) == 1:
                output[key] = rows[0]["c"]
            else:
                output[key] = [dict(row) for row in rows]
    finally:
        db.close()

    print(json.dumps(output, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()