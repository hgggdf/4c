"""OpenClaw 数据包一键入库脚本（直接调用 service 层）。

用法:
    python import_batch.py data/incoming/all_20260426_001
    python import_batch.py --all
"""

import json
import hashlib
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database.session import SessionLocal
from app.core.database.models.company import Company, IndustryMaster
from app.core.database.models.financial_hot import FinancialHot
from app.core.database.models.announcement_hot import AnnouncementHot
from app.core.database.models.research_report_hot import ResearchReportHot
from app.core.database.models.news_hot import NewsHot
from app.core.database.models.macro_hot import MacroIndicator
from sqlalchemy import select

INCOMING_DIR = Path("data/incoming")
PROCESSED_DIR = Path("data/processed")
FAILED_DIR = Path("data/failed")
RAW_FILES_DIR = Path("data/raw_files")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                log(f"  WARN: {path.name} 第{i}行 JSON 解析失败: {e}")
    return records


def move_file_to_raw(batch_dir: Path, local_file: str, category: str, sub_key: str) -> str | None:
    if not local_file:
        return None
    src = batch_dir / category / local_file
    if not src.exists():
        src = batch_dir / local_file
    if not src.exists():
        return None
    year = datetime.now().strftime("%Y")
    dest_dir = RAW_FILES_DIR / category / year / sub_key
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.exists():
        dest = dest_dir / f"{sha256(str(time.time()))}_{src.name}"
    shutil.copy2(str(src), str(dest))
    return str(dest.relative_to(Path("data")))


def _safe_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _compute_ratio(numerator, denominator):
    n = _safe_float(numerator)
    d = _safe_float(denominator)
    if n is None or d is None or d == 0:
        return None
    return round(n / d, 6)


# ── 各类型入库逻辑（直接操作数据库）──────────────────────

def ingest_company(batch_id: str, batch_dir: Path, records: list[dict]) -> tuple[int, int, list]:
    ok, fail, errors = 0, 0, []
    db = SessionLocal()
    try:
        for i, rec in enumerate(records):
            stock_code = rec.get("stock_code", "")
            if not stock_code:
                errors.append({"row": i + 1, "reason": "stock_code 为空"})
                fail += 1
                continue
            try:
                existing = db.execute(
                    select(Company).where(Company.stock_code == stock_code)
                ).scalars().first()
                if existing:
                    for field in ["stock_name", "full_name", "exchange", "industry_level1",
                                  "industry_level2", "listing_date", "business_summary",
                                  "core_products_json", "main_segments_json"]:
                        val = rec.get(field)
                        if val is not None:
                            setattr(existing, field, val)
                    if rec.get("industry_code"):
                        ind = db.execute(select(IndustryMaster).where(
                            IndustryMaster.industry_code == rec["industry_code"]
                        )).scalars().first()
                        if ind:
                            existing.industry_code = rec["industry_code"]
                else:
                    industry_code = rec.get("industry_code")
                    if industry_code:
                        ind = db.execute(select(IndustryMaster).where(
                            IndustryMaster.industry_code == industry_code
                        )).scalars().first()
                        if not ind:
                            industry_code = None
                    company = Company(
                        stock_code=stock_code,
                        stock_name=rec.get("stock_name", stock_code),
                        full_name=rec.get("full_name"),
                        exchange=rec.get("exchange"),
                        industry_level1=rec.get("industry_level1", "医药生物"),
                        industry_code=industry_code,
                        industry_level2=rec.get("industry_level2"),
                        listing_date=rec.get("listing_date"),
                        business_summary=rec.get("business_summary"),
                        core_products_json=rec.get("core_products_json"),
                        main_segments_json=rec.get("main_segments_json"),
                    )
                    db.add(company)
                db.flush()
                ok += 1
            except Exception as e:
                errors.append({"row": i + 1, "reason": str(e)})
                fail += 1
                db.rollback()
        db.commit()
    finally:
        db.close()
    return ok, fail, errors


def ingest_financial(batch_id: str, batch_dir: Path, records: list[dict]) -> tuple[int, int, list]:
    ok, fail, errors = 0, 0, []
    db = SessionLocal()
    try:
        for i, rec in enumerate(records):
            stock_code = rec.get("stock_code", "")
            report_date = rec.get("report_date", "")
            if not stock_code or not report_date:
                errors.append({"row": i + 1, "reason": "stock_code 或 report_date 为空"})
                fail += 1
                continue
            try:
                file_path = move_file_to_raw(batch_dir, rec.get("local_file", ""), "financial", stock_code)
                report_type = rec.get("report_type", "annual")
                fiscal_year = int(report_date[:4]) if len(report_date) >= 4 else None
                revenue = _safe_float(rec.get("revenue"))
                operating_cost = _safe_float(rec.get("operating_cost"))

                existing = db.execute(
                    select(FinancialHot).where(
                        FinancialHot.stock_code == stock_code,
                        FinancialHot.report_date == report_date,
                        FinancialHot.report_type == report_type,
                    )
                ).scalars().first()

                values = {
                    "fiscal_year": fiscal_year,
                    "revenue": revenue,
                    "operating_cost": operating_cost,
                    "gross_profit": (revenue - operating_cost) if revenue is not None and operating_cost is not None else rec.get("gross_profit"),
                    "gross_margin": _compute_ratio((revenue or 0) - (operating_cost or 0), revenue) if revenue and operating_cost else None,
                    "selling_expense": _safe_float(rec.get("selling_expense")),
                    "admin_expense": _safe_float(rec.get("admin_expense")),
                    "rd_expense": _safe_float(rec.get("rd_expense")),
                    "rd_ratio": _compute_ratio(rec.get("rd_expense"), revenue),
                    "operating_profit": _safe_float(rec.get("operating_profit")),
                    "net_profit": _safe_float(rec.get("net_profit")),
                    "net_profit_deducted": _safe_float(rec.get("net_profit_deducted")),
                    "eps": _safe_float(rec.get("eps")),
                    "total_assets": _safe_float(rec.get("total_assets")),
                    "total_liabilities": _safe_float(rec.get("total_liabilities")),
                    "debt_ratio": _compute_ratio(rec.get("total_liabilities"), rec.get("total_assets")),
                    "operating_cashflow": _safe_float(rec.get("operating_cashflow")),
                    "investing_cashflow": _safe_float(rec.get("investing_cashflow")),
                    "financing_cashflow": _safe_float(rec.get("financing_cashflow")),
                    "trade_date": rec.get("trade_date"),
                    "open_price": _safe_float(rec.get("open_price")),
                    "close_price": _safe_float(rec.get("close_price")),
                    "high_price": _safe_float(rec.get("high_price")),
                    "low_price": _safe_float(rec.get("low_price")),
                    "volume": _safe_float(rec.get("volume")),
                    "amount": _safe_float(rec.get("amount")),
                    "change_pct": _safe_float(rec.get("change_pct")),
                    "source_url": rec.get("source_url"),
                    "file_path": file_path,
                    "original_filename": rec.get("original_filename"),
                    "file_hash": rec.get("file_hash"),
                }
                # 只更新非 None 的值
                values = {k: v for k, v in values.items() if v is not None}

                if existing:
                    for k, v in values.items():
                        setattr(existing, k, v)
                else:
                    entity = FinancialHot(
                        stock_code=stock_code,
                        report_date=report_date,
                        report_type=report_type,
                        **values,
                    )
                    db.add(entity)
                db.flush()
                ok += 1
            except Exception as e:
                errors.append({"row": i + 1, "reason": str(e)})
                fail += 1
                db.rollback()
        db.commit()
    finally:
        db.close()
    return ok, fail, errors


def ingest_announcement(batch_id: str, batch_dir: Path, records: list[dict]) -> tuple[int, int, list]:
    ok, fail, errors = 0, 0, []
    db = SessionLocal()
    try:
        for i, rec in enumerate(records):
            stock_code = rec.get("stock_code", "")
            title = rec.get("title", "")
            publish_date = rec.get("publish_date", "")
            if not stock_code or not title or not publish_date:
                errors.append({"row": i + 1, "reason": "stock_code/title/publish_date 为空"})
                fail += 1
                continue
            try:
                move_file_to_raw(batch_dir, rec.get("local_file", ""), "announcement", stock_code)
                uid = md5(f"{stock_code}-{title}-{publish_date}")

                existing = db.execute(
                    select(AnnouncementHot).where(
                        AnnouncementHot.stock_code == stock_code,
                        AnnouncementHot.title == title,
                        AnnouncementHot.publish_date == publish_date,
                    )
                ).scalars().first()

                if existing:
                    for field in ["announcement_type", "content", "summary_text",
                                  "key_fields_json", "source_url", "file_hash"]:
                        val = rec.get(field)
                        if val is not None:
                            setattr(existing, field, val)
                else:
                    entity = AnnouncementHot(
                        announcement_uid=uid,
                        stock_code=stock_code,
                        title=title,
                        publish_date=publish_date,
                        announcement_type=rec.get("announcement_type"),
                        content=rec.get("content"),
                        summary_text=rec.get("summary_text"),
                        key_fields_json=rec.get("key_fields_json"),
                        source_url=rec.get("source_url"),
                        file_hash=rec.get("file_hash") or uid,
                    )
                    db.add(entity)
                db.flush()
                ok += 1
            except Exception as e:
                errors.append({"row": i + 1, "reason": str(e)})
                fail += 1
                db.rollback()
        db.commit()
    finally:
        db.close()
    return ok, fail, errors


def ingest_research_report(batch_id: str, batch_dir: Path, records: list[dict]) -> tuple[int, int, list]:
    ok, fail, errors = 0, 0, []
    db = SessionLocal()
    try:
        for i, rec in enumerate(records):
            title = rec.get("title", "")
            if not title:
                errors.append({"row": i + 1, "reason": "title 为空"})
                fail += 1
                continue
            try:
                scope_type = rec.get("scope_type", "company")
                stock_code = rec.get("stock_code") or None
                industry_code = rec.get("industry_code") or None
                sub_key = stock_code or industry_code or "unknown"
                move_file_to_raw(batch_dir, rec.get("local_file", ""), "research_report", sub_key)

                # 校验外键
                if stock_code:
                    exists = db.execute(select(Company).where(Company.stock_code == stock_code)).scalars().first()
                    if not exists:
                        stock_code = None
                if industry_code:
                    exists = db.execute(select(IndustryMaster).where(IndustryMaster.industry_code == industry_code)).scalars().first()
                    if not exists:
                        industry_code = None

                uid = md5(f"{scope_type}-{stock_code}-{industry_code}-{title}-{rec.get('publish_date', '')}")

                existing = db.execute(
                    select(ResearchReportHot).where(ResearchReportHot.report_uid == uid)
                ).scalars().first()

                if existing:
                    for field in ["report_org", "content", "summary_text", "source_type",
                                  "source_url", "file_hash"]:
                        val = rec.get(field)
                        if val is not None:
                            setattr(existing, field, val)
                else:
                    entity = ResearchReportHot(
                        report_uid=uid,
                        scope_type=scope_type,
                        stock_code=stock_code,
                        industry_code=industry_code,
                        title=title,
                        publish_date=rec.get("publish_date"),
                        report_org=rec.get("report_org"),
                        content=rec.get("content"),
                        summary_text=rec.get("summary_text"),
                        source_type=rec.get("source_type"),
                        source_url=rec.get("source_url"),
                        file_hash=rec.get("file_hash"),
                    )
                    db.add(entity)
                db.flush()
                ok += 1
            except Exception as e:
                errors.append({"row": i + 1, "reason": str(e)})
                fail += 1
                db.rollback()
        db.commit()
    finally:
        db.close()
    return ok, fail, errors


def ingest_news(batch_id: str, batch_dir: Path, records: list[dict]) -> tuple[int, int, list]:
    ok, fail, errors = 0, 0, []
    db = SessionLocal()
    try:
        for i, rec in enumerate(records):
            title = rec.get("title", "")
            if not title:
                errors.append({"row": i + 1, "reason": "title 为空"})
                fail += 1
                continue
            try:
                move_file_to_raw(batch_dir, rec.get("local_file", ""), "news",
                                 datetime.now().strftime("%Y/%m"))
                news_uid = sha256(
                    rec.get("source_url") or f"{title}{rec.get('publish_time', '')}{rec.get('source_name', '')}"
                )

                existing = db.execute(
                    select(NewsHot).where(NewsHot.news_uid == news_uid)
                ).scalars().first()

                if existing:
                    for field in ["content", "summary_text", "news_type", "source_name",
                                  "source_url", "related_stock_codes_json",
                                  "related_industry_codes_json", "key_fields_json"]:
                        val = rec.get(field)
                        if val is not None:
                            setattr(existing, field, val)
                else:
                    entity = NewsHot(
                        news_uid=news_uid,
                        title=title,
                        publish_time=rec.get("publish_time"),
                        source_name=rec.get("source_name"),
                        source_url=rec.get("source_url"),
                        news_type=rec.get("news_type"),
                        content=rec.get("content"),
                        summary_text=rec.get("summary_text"),
                        related_stock_codes_json=rec.get("related_stock_codes_json"),
                        related_industry_codes_json=rec.get("related_industry_codes_json"),
                        key_fields_json=rec.get("key_fields_json"),
                        file_hash=rec.get("file_hash"),
                    )
                    db.add(entity)
                db.flush()
                ok += 1
            except Exception as e:
                errors.append({"row": i + 1, "reason": str(e)})
                fail += 1
                db.rollback()
        db.commit()
    finally:
        db.close()
    return ok, fail, errors


def ingest_macro(batch_id: str, batch_dir: Path, records: list[dict]) -> tuple[int, int, list]:
    ok, fail, errors = 0, 0, []
    db = SessionLocal()
    try:
        for i, rec in enumerate(records):
            indicator_name = rec.get("indicator_name", "")
            period = rec.get("period", "")
            if not indicator_name or not period:
                errors.append({"row": i + 1, "reason": "indicator_name 或 period 为空"})
                fail += 1
                continue
            try:
                existing = db.execute(
                    select(MacroIndicator).where(
                        MacroIndicator.indicator_name == indicator_name,
                        MacroIndicator.period == period,
                    )
                ).scalars().first()

                if existing:
                    for field in ["value", "unit", "category", "summary_text",
                                  "source_type", "source_url"]:
                        val = rec.get(field)
                        if val is not None:
                            setattr(existing, field, val)
                else:
                    entity = MacroIndicator(
                        indicator_name=indicator_name,
                        period=period,
                        period_date=rec.get("period_date"),
                        value=_safe_float(rec.get("value")),
                        unit=rec.get("unit"),
                        category=rec.get("category"),
                        summary_text=rec.get("summary_text"),
                        source_type=rec.get("source_type"),
                        source_url=rec.get("source_url"),
                    )
                    db.add(entity)
                db.flush()
                ok += 1
            except Exception as e:
                errors.append({"row": i + 1, "reason": str(e)})
                fail += 1
                db.rollback()
        db.commit()
    finally:
        db.close()
    return ok, fail, errors


# ── 主流程 ──────────────────────────────────────────────

HANDLERS = {
    "company":         ("company/company_records.jsonl",                 ingest_company),
    "financial":       ("financial/financial_records.jsonl",             ingest_financial),
    "announcement":    ("announcement/announcement_records.jsonl",      ingest_announcement),
    "research_report": ("research_report/research_report_records.jsonl", ingest_research_report),
    "news":            ("news/news_records.jsonl",                      ingest_news),
    "macro":           ("macro/macro_records.jsonl",                    ingest_macro),
}

TABLE_ORDER = ["company", "financial", "announcement", "research_report", "news", "macro"]


def process_batch(batch_dir: Path):
    manifest_path = batch_dir / "manifest.json"
    if not manifest_path.exists():
        log(f"ERROR: {batch_dir} 下找不到 manifest.json")
        return False

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    batch_id = manifest.get("batch_id", batch_dir.name)
    status = manifest.get("status", "")
    if status != "ready":
        log(f"SKIP: {batch_id} status={status}，不是 ready")
        return False

    data_types = manifest.get("data_types", [])
    files_map = manifest.get("files", {})
    log(f"开始处理批次: {batch_id}  数据类型: {data_types}")

    total_ok, total_fail = 0, 0
    all_errors = []

    for dtype in TABLE_ORDER:
        if dtype not in data_types:
            continue
        jsonl_rel = files_map.get(dtype) or HANDLERS.get(dtype, (None,))[0]
        if not jsonl_rel:
            continue
        handler_info = HANDLERS.get(dtype)
        if not handler_info:
            log(f"  WARN: 未知数据类型 {dtype}，跳过")
            continue
        _, handler_fn = handler_info
        jsonl_path = batch_dir / jsonl_rel
        records = read_jsonl(jsonl_path)
        if not records:
            log(f"  {dtype}: 0 条记录，跳过")
            continue
        log(f"  {dtype}: 读取 {len(records)} 条，开始入库...")
        t0 = time.time()
        ok, fail, errs = handler_fn(batch_id, batch_dir, records)
        elapsed = time.time() - t0
        total_ok += ok
        total_fail += fail
        all_errors.extend(errs)
        log(f"  {dtype}: 成功 {ok}，失败 {fail}  ({elapsed:.1f}s)")

    log(f"批次 {batch_id} 完成: 成功 {total_ok}，失败 {total_fail}")

    if total_fail > 0 and total_ok == 0:
        dest = FAILED_DIR / batch_id
        dest.mkdir(parents=True, exist_ok=True)
        report = {"batch_id": batch_id, "status": "failed", "failed_at": datetime.now().isoformat(),
                  "success_count": total_ok, "failed_count": total_fail, "errors": all_errors[:100]}
        with open(dest / "error_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        if batch_dir.resolve() != dest.resolve():
            shutil.copytree(str(batch_dir), str(dest), dirs_exist_ok=True)
        log(f"批次已移动到 {dest}")
        return False

    dest = PROCESSED_DIR / batch_id
    dest.mkdir(parents=True, exist_ok=True)
    report = {"batch_id": batch_id, "status": "success" if total_fail == 0 else "partial",
              "finished_at": datetime.now().isoformat(), "success_count": total_ok,
              "failed_count": total_fail, "errors": all_errors[:100]}
    with open(dest / "import_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    if batch_dir.resolve() != dest.resolve():
        shutil.copytree(str(batch_dir), str(dest), dirs_exist_ok=True)
    log(f"批次已移动到 {dest}")
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    if sys.argv[1] == "--all":
        if not INCOMING_DIR.exists():
            log(f"目录不存在: {INCOMING_DIR}")
            sys.exit(1)
        batches = sorted([d for d in INCOMING_DIR.iterdir() if d.is_dir()])
        if not batches:
            log("没有待处理的批次")
            sys.exit(0)
        log(f"发现 {len(batches)} 个待处理批次")
        for batch_dir in batches:
            process_batch(batch_dir)
    else:
        batch_dir = Path(sys.argv[1])
        if not batch_dir.exists():
            log(f"目录不存在: {batch_dir}")
            sys.exit(1)
        process_batch(batch_dir)


if __name__ == "__main__":
    main()
