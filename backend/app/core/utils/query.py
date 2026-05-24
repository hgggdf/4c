from __future__ import annotations

from typing import Any, Iterable


def latest_rows_by_year(rows: Iterable, year_attr: str) -> dict[int, Any]:
    grouped: dict[int, Any] = {}
    for row in rows:
        year = getattr(row, year_attr, None)
        if year is None:
            report_date = getattr(row, "report_date", None)
            year = report_date.year if report_date is not None else None
        if year is None or int(year) in grouped:
            continue
        grouped[int(year)] = row
    return grouped
