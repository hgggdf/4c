from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import delete, select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.dialogue_agent import DialogueAgent
from agent.integration.langgraph_agent import tool_get_price_volume_data
from agent.integration.tool_executor import execute_tool_plan
from agent.integration.tool_planner import build_tool_plan
from agent.tools.price_volume_tools import get_price_volume_analysis, get_price_volume_data
from app.core.database.models.company import Company
from app.core.database.models.financial_hot import FinancialArchive, FinancialHot
from app.core.database.session import SessionLocal
from app.router.openclaw_ingest import OpenClawEnvelope, _ingest_stock_daily
from app.service.container import ServiceContainer
from app.service.write_requests import BatchUpsertFinancialRequest


TEST_STOCK_CODE = "689971"
TEST_STOCK_NAME = "Codex量价测试"


def _reset_test_rows() -> None:
    db = SessionLocal()
    try:
        db.execute(delete(FinancialHot).where(FinancialHot.stock_code == TEST_STOCK_CODE))
        db.execute(delete(FinancialArchive).where(FinancialArchive.stock_code == TEST_STOCK_CODE))
        company = db.execute(select(Company).where(Company.stock_code == TEST_STOCK_CODE)).scalar_one_or_none()
        if company is None:
            db.add(
                Company(
                    stock_code=TEST_STOCK_CODE,
                    stock_name=TEST_STOCK_NAME,
                    exchange="SSE",
                    industry_level1="医药生物",
                    industry_level2="量价测试",
                )
            )
        else:
            company.stock_name = TEST_STOCK_NAME
        db.commit()
    finally:
        db.close()


def _seed_daily_rows_via_service() -> None:
    items = []
    start = date(2026, 1, 2)
    prev_close = 50.0
    for index in range(45):
        day = start + timedelta(days=index)
        open_price = round(prev_close + 0.05, 4)
        close_price = round(50 + index * 0.18 + (0.6 if index % 7 == 0 else -0.2), 4)
        high_price = round(max(open_price, close_price) + 0.45, 4)
        low_price = round(min(open_price, close_price) - 0.35, 4)
        volume = 100000 + index * 2500 + (90000 if index in (18, 32) else 0)
        change_pct = round((close_price - prev_close) / prev_close, 6)
        items.append(
            {
                "stock_code": TEST_STOCK_CODE,
                "trade_date": day.isoformat(),
                "open_price": open_price,
                "close_price": close_price,
                "high_price": high_price,
                "low_price": low_price,
                "volume": volume,
                "amount": round(volume * close_price, 2),
                "change_pct": change_pct,
                "source_url": "https://codex.test/price-volume",
            }
        )
        prev_close = close_price

    container = ServiceContainer.build_default()
    result = container.financial_write.batch_upsert_stock_daily(BatchUpsertFinancialRequest(items=items))
    assert result.success, result.message
    assert result.data["total"] == len(items), result.data


def _move_old_daily_rows_to_archive() -> None:
    db = SessionLocal()
    try:
        old_rows = (
            db.execute(
                select(FinancialHot)
                .where(
                    FinancialHot.stock_code == TEST_STOCK_CODE,
                    FinancialHot.report_type == "daily",
                    FinancialHot.report_date < date(2026, 1, 17),
                )
                .order_by(FinancialHot.report_date.asc())
            )
            .scalars()
            .all()
        )
        archive_cols = {column.key for column in FinancialArchive.__table__.columns}
        for row in old_rows:
            payload = {
                col: getattr(row, col)
                for col in archive_cols
                if col != "id" and hasattr(row, col)
            }
            existing = db.execute(
                select(FinancialArchive).where(FinancialArchive.dedup_key == row.dedup_key)
            ).scalar_one_or_none()
            if existing is None:
                db.add(FinancialArchive(**payload))
            else:
                for key, value in payload.items():
                    setattr(existing, key, value)
            db.delete(row)
        db.commit()
    finally:
        db.close()


def _seed_one_daily_row_via_openclaw() -> None:
    envelope = OpenClawEnvelope(
        batch_id="codex_price_volume_test",
        task_id="codex_price_volume_test_001",
        source={
            "source_type": "codex_test",
            "source_url": "https://codex.test/openclaw/price-volume",
        },
        entity={"stock_code": TEST_STOCK_CODE, "stock_name": TEST_STOCK_NAME},
        document={},
        payload_type="stock_daily",
        payload={
            "trade_date": "2026-02-16",
            "open_price": 58.1,
            "close_price": 58.6,
            "high_price": 59.0,
            "low_price": 57.9,
            "volume": 260000,
            "turnover": 15236000,
            "change_pct": 0.0123,
        },
        processing={},
        extra={},
    )
    response = _ingest_stock_daily(envelope, ServiceContainer.build_default())
    assert response.status_code == 200, response.body


def main() -> None:
    _reset_test_rows()
    _seed_daily_rows_via_service()
    _move_old_daily_rows_to_archive()
    _seed_one_daily_row_via_openclaw()

    raw = get_price_volume_data(TEST_STOCK_CODE, days=40)
    assert "error" not in raw, raw
    assert raw["count"] == 40, raw
    assert raw["latest"]["date"] == "2026-02-16", raw["latest"]

    analysis = get_price_volume_analysis(TEST_STOCK_CODE, days=40)
    assert analysis["data_days"] == 40, analysis
    assert analysis["price_trend"]["ma5"] is not None, analysis
    assert analysis["volume_trend"]["vol_ma10"] is not None, analysis
    assert analysis["correlation"]["pearson_20d"] is not None, analysis

    plan = build_tool_plan(
        f"请分析{TEST_STOCK_NAME}最近40个交易日的量价表现",
        selected_mode="price_volume_analysis",
        company_entity={"stock_code": TEST_STOCK_CODE, "company_name": TEST_STOCK_NAME},
    )
    results = execute_tool_plan(plan, dry_run=False)
    pv_result = next(item for item in results if item["tool_name"] == "price_volume_analysis")
    assert pv_result["success"], pv_result
    assert pv_result["data"]["data_days"] == 40, pv_result

    follow_up_question = DialogueAgent._build_tool_planning_question(
        "2月16日呢？",
        history=[
            {
                "role": "user",
                "content": f"请分析{TEST_STOCK_NAME}最近40个交易日的量价表现，给出MA和量比。",
            }
        ],
        db_messages=None,
    )
    follow_up_plan = build_tool_plan(
        follow_up_question,
        selected_mode="quick_query",
        company_entity={"stock_code": TEST_STOCK_CODE, "company_name": TEST_STOCK_NAME},
    )
    follow_up_names = [item["tool_name"] for item in follow_up_plan]
    assert "price_volume_data" in follow_up_names, follow_up_names
    follow_up_results = execute_tool_plan(follow_up_plan, dry_run=False)
    raw_result = next(item for item in follow_up_results if item["tool_name"] == "price_volume_data")
    assert raw_result["success"], raw_result
    assert "2026-02-16" in raw_result["data"]["trade_dates"], raw_result["data"]["trade_dates"]

    exact = get_price_volume_data(TEST_STOCK_CODE, days=1, target_date="2月16日")
    assert exact["target_match"]["matched_date"] == "2026-02-16", exact
    assert exact["target_record"]["close"] == 58.6, exact["target_record"]
    assert exact["target_record"]["change_pct"] == 1.23, exact["target_record"]

    guarded = tool_get_price_volume_data.invoke({"stock_code": TEST_STOCK_CODE, "days": 1})
    assert guarded["effective_days"] == 60, guarded
    assert "2026-02-16" in guarded["trade_dates"], guarded["trade_dates"]

    print("price-volume daily ingest/read/tool-plan chain passed")


if __name__ == "__main__":
    main()
