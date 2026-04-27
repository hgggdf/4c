"""
import_worker.py
===============
OpenClaw 数据包入库主流程。

调用方式（程序内）：
    from ingest_center.import_worker import ImportWorker
    result = ImportWorker(db).run_batch("data/incoming/all_20260426_001")

流程：
    1. 读取 manifest.json，检查 batch_id 是否已处理
    2. 校验文件结构
    3. 按数据类型依次：写 staging → 校验 → 移动文件 → merge 到正式表
    4. 触发向量化队列（标记 vector_status=pending）
    5. 移动 batch 到 processed/ 或 failed/
    6. 写 data_job_log
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from datetime import datetime, date
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import text, select

from app.core.database.models.vector_and_job import DataJobLog, StagingImport
from app.core.database.models.financial_hot import FinancialHot
from app.core.database.models.announcement_hot import AnnouncementHot
from app.core.database.models.research_report_hot import ResearchReportHot
from app.core.database.models.news_hot import NewsHot
from app.core.database.models.macro_hot import MacroIndicator
from app.core.database.models.company import Company, IndustryMaster

logger = logging.getLogger(__name__)

# 批量提交大小（防死锁关键参数）
CHUNK_SIZE = 2000

# 正式文件存放根目录
RAW_FILES_ROOT = Path("data/raw_files")
INCOMING_ROOT = Path("data/incoming")
PROCESSED_ROOT = Path("data/processed")
FAILED_ROOT = Path("data/failed")


class ImportWorker:
    """OpenClaw 数据包入库 Worker。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def run_batch(self, batch_dir: str | Path) -> dict:
        """
        处理一个 batch 目录，返回入库结果摘要。

        Args:
            batch_dir: data/incoming/{batch_id} 目录路径

        Returns:
            {"batch_id": ..., "status": "success"|"failed", "success_count": ..., "failed_count": ...}
        """
        batch_path = Path(batch_dir)
        manifest_path = batch_path / "manifest.json"

        job = self._create_job_log("import_batch", "multiple", batch_id=batch_path.name)

        try:
            manifest = self._load_manifest(manifest_path)
            batch_id = manifest["batch_id"]

            if self._is_already_processed(batch_id):
                logger.info("batch %s already processed, skip", batch_id)
                self._finish_job(job, "skipped", 0, 0)
                return {"batch_id": batch_id, "status": "skipped"}

            self._validate_structure(batch_path, manifest)

            total_success = 0
            total_failed = 0

            # 按固定顺序处理各数据类型（防死锁）
            for data_type in ["financial", "announcement", "research_report", "news", "macro"]:
                if data_type not in manifest.get("data_types", []):
                    continue
                s, f = self._process_data_type(batch_path, batch_id, data_type, manifest)
                total_success += s
                total_failed += f

            if total_failed == 0:
                self._move_batch(batch_path, PROCESSED_ROOT / batch_id)
                self._finish_job(job, "success", total_success, total_failed)
                return {"batch_id": batch_id, "status": "success", "success_count": total_success, "failed_count": 0}
            else:
                self._write_error_report(batch_path, batch_id, total_failed)
                self._move_batch(batch_path, FAILED_ROOT / batch_id)
                self._finish_job(job, "partial_failed", total_success, total_failed)
                return {"batch_id": batch_id, "status": "partial_failed", "success_count": total_success, "failed_count": total_failed}

        except Exception as exc:
            logger.exception("batch import failed: %s", exc)
            self._finish_job(job, "failed", 0, 0, error=str(exc))
            try:
                self._move_batch(batch_path, FAILED_ROOT / batch_path.name)
            except Exception:
                pass
            return {"batch_id": batch_path.name, "status": "failed", "error": str(exc)}

    # ------------------------------------------------------------------
    # 内部流程
    # ------------------------------------------------------------------

    def _process_data_type(self, batch_path: Path, batch_id: str, data_type: str, manifest: dict) -> tuple[int, int]:
        """处理单个数据类型，返回 (success_count, failed_count)。"""
        jsonl_rel = manifest["files"].get(data_type)
        if not jsonl_rel:
            return 0, 0

        jsonl_path = batch_path / jsonl_rel
        if not jsonl_path.exists():
            logger.warning("jsonl not found: %s", jsonl_path)
            return 0, 1

        records = self._read_jsonl(jsonl_path)
        if not records:
            return 0, 0

        # 写 staging
        self._write_staging(batch_id, data_type, records)

        # 校验 + 移动文件
        valid_records, failed_count = self._validate_and_move_files(
            batch_path, batch_id, data_type, records
        )

        # 批量 merge 到正式表（小批量提交，防死锁）
        success_count = self._merge_to_hot(batch_id, data_type, valid_records)

        # 清理 staging
        self._cleanup_staging(batch_id, data_type)

        return success_count, failed_count

    def _write_staging(self, batch_id: str, data_type: str, records: list[dict]) -> None:
        """批量写入 staging 临时表。"""
        for i in range(0, len(records), CHUNK_SIZE):
            chunk = records[i:i + CHUNK_SIZE]
            items = [
                StagingImport(
                    batch_id=batch_id,
                    data_type=data_type,
                    row_no=i + j,
                    import_status="pending",
                    raw_json=json.dumps(rec, ensure_ascii=False),
                )
                for j, rec in enumerate(chunk)
            ]
            self.db.add_all(items)
            self.db.flush()

    def _validate_and_move_files(
        self, batch_path: Path, batch_id: str, data_type: str, records: list[dict]
    ) -> tuple[list[dict], int]:
        """校验记录并移动原始文件，返回 (valid_records, failed_count)。"""
        valid = []
        failed = 0

        for rec in records:
            local_file = rec.get("local_file")
            if local_file:
                src = batch_path / data_type / local_file
                if not src.exists():
                    logger.warning("file not found: %s", src)
                    failed += 1
                    continue

                # 计算 file_hash
                file_hash = _sha256_file(src)

                # 生成正式路径
                dest_dir = _get_dest_dir(data_type, rec)
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_name = _build_dest_filename(rec, file_hash, src.suffix)
                dest = dest_dir / dest_name

                if not dest.exists():
                    shutil.copy2(src, dest)

                rec = {**rec, "file_path": str(dest), "file_hash": file_hash, "file_type": src.suffix.lstrip(".")}

            valid.append(rec)

        return valid, failed

    def _merge_to_hot(self, batch_id: str, data_type: str, records: list[dict]) -> int:
        """批量 merge 到正式热库表，小批量提交。"""
        if not records:
            return 0

        merger = _MERGERS.get(data_type)
        if merger is None:
            logger.warning("no merger for data_type: %s", data_type)
            return 0

        success = 0
        for i in range(0, len(records), CHUNK_SIZE):
            chunk = records[i:i + CHUNK_SIZE]
            try:
                success += merger(self.db, chunk)
                self.db.commit()
            except Exception as exc:
                logger.error("merge chunk failed: %s", exc)
                self.db.rollback()

        return success

    def _cleanup_staging(self, batch_id: str, data_type: str) -> None:
        self.db.execute(
            text("DELETE FROM staging_import WHERE batch_id = :bid AND data_type = :dt"),
            {"bid": batch_id, "dt": data_type},
        )
        self.db.commit()

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _load_manifest(self, path: Path) -> dict:
        if not path.exists():
            raise FileNotFoundError(f"manifest.json not found: {path}")
        with open(path, encoding="utf-8") as f:
            manifest = json.load(f)
        if manifest.get("status") != "ready":
            raise ValueError(f"manifest status is not ready: {manifest.get('status')}")
        return manifest

    def _is_already_processed(self, batch_id: str) -> bool:
        row = self.db.execute(
            text("SELECT id FROM data_job_log WHERE batch_id = :bid AND job_status = 'success' LIMIT 1"),
            {"bid": batch_id},
        ).fetchone()
        return row is not None

    def _validate_structure(self, batch_path: Path, manifest: dict) -> None:
        for data_type, rel_path in manifest.get("files", {}).items():
            p = batch_path / rel_path
            if not p.exists():
                raise FileNotFoundError(f"JSONL not found: {p}")

    def _read_jsonl(self, path: Path) -> list[dict]:
        records = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def _move_batch(self, src: Path, dest: Path) -> None:
        if src.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                shutil.rmtree(dest)
            shutil.move(str(src), str(dest))
        self._cleanup_incoming()

    def _cleanup_incoming(self) -> None:
        """清理 incoming 根目录里已处理完的空目录和散落文件，防止重复入库。"""
        if not INCOMING_ROOT.exists():
            return
        for item in list(INCOMING_ROOT.iterdir()):
            try:
                if item.is_dir():
                    # 只删除空目录（有内容的说明还未处理）
                    if not any(item.iterdir()):
                        item.rmdir()
                        logger.info("cleaned empty incoming dir: %s", item.name)
                else:
                    # 散落文件直接删除
                    item.unlink()
                    logger.info("cleaned stray incoming file: %s", item.name)
            except Exception as exc:
                logger.warning("cleanup_incoming skip %s: %s", item.name, exc)

    def _write_error_report(self, batch_path: Path, batch_id: str, failed_count: int) -> None:
        report = {
            "batch_id": batch_id,
            "status": "partial_failed",
            "failed_at": datetime.now().isoformat(sep=" ", timespec="seconds"),
            "failed_count": failed_count,
        }
        with open(batch_path / "error_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    def _create_job_log(self, job_type: str, target_table: str, batch_id: str | None = None) -> DataJobLog:
        job = DataJobLog(
            batch_id=batch_id,
            job_type=job_type,
            target_table=target_table,
            job_status="running",
            started_at=datetime.now(),
        )
        self.db.add(job)
        self.db.flush()
        return job

    def _finish_job(self, job: DataJobLog, status: str, success: int, failed: int, error: str | None = None) -> None:
        job.job_status = status
        job.success_count = success
        job.failed_count = failed
        job.finished_at = datetime.now()
        if error:
            job.error_message = error
        self.db.commit()


# ------------------------------------------------------------------
# 各数据类型 merge 函数
# ------------------------------------------------------------------

def _merge_financial(db: Session, records: list[dict]) -> int:
    count = 0
    for rec in sorted(records, key=lambda r: (r.get("stock_code", ""), str(r.get("report_date", "")), r.get("report_type", ""))):
        try:
            _upsert_financial(db, rec)
            count += 1
        except Exception as exc:
            logger.warning("financial upsert failed: %s | %s", exc, rec.get("stock_code"))
    return count


def _upsert_financial(db: Session, rec: dict) -> None:
    report_date = _parse_date(rec.get("report_date"))
    if not report_date:
        return

    revenue = _decimal(rec.get("revenue"))
    operating_cost = _decimal(rec.get("operating_cost"))
    total_assets = _decimal(rec.get("total_assets"))
    total_liabilities = _decimal(rec.get("total_liabilities"))
    rd_expense = _decimal(rec.get("rd_expense"))

    gross_profit = (revenue - operating_cost) if revenue is not None and operating_cost is not None else None
    gross_margin = (gross_profit / revenue) if gross_profit is not None and revenue and revenue != 0 else None
    rd_ratio = (rd_expense / revenue) if rd_expense is not None and revenue and revenue != 0 else None
    debt_ratio = (total_liabilities / total_assets) if total_liabilities is not None and total_assets and total_assets != 0 else None

    existing = db.execute(
        select(FinancialHot).where(
            FinancialHot.stock_code == rec["stock_code"],
            FinancialHot.report_date == report_date,
            FinancialHot.report_type == rec.get("report_type"),
        )
    ).scalar_one_or_none()

    fields = dict(
        fiscal_year=report_date.year,
        revenue=revenue,
        operating_cost=operating_cost,
        gross_profit=gross_profit,
        gross_margin=gross_margin,
        selling_expense=_decimal(rec.get("selling_expense")),
        admin_expense=_decimal(rec.get("admin_expense")),
        rd_expense=rd_expense,
        rd_ratio=rd_ratio,
        operating_profit=_decimal(rec.get("operating_profit")),
        net_profit=_decimal(rec.get("net_profit")),
        net_profit_deducted=_decimal(rec.get("net_profit_deducted")),
        eps=_decimal(rec.get("eps")),
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        debt_ratio=debt_ratio,
        operating_cashflow=_decimal(rec.get("operating_cashflow")),
        investing_cashflow=_decimal(rec.get("investing_cashflow")),
        financing_cashflow=_decimal(rec.get("financing_cashflow")),
        source_url=rec.get("source_url"),
        file_path=rec.get("file_path"),
        file_type=rec.get("file_type"),
        original_filename=rec.get("original_filename"),
        file_hash=rec.get("file_hash"),
    )

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(FinancialHot(
            stock_code=rec["stock_code"],
            report_date=report_date,
            report_type=rec.get("report_type"),
            query_count=0,
            **fields,
        ))
    db.flush()


def _merge_announcement(db: Session, records: list[dict]) -> int:
    count = 0
    for rec in sorted(records, key=lambda r: (r.get("stock_code", ""), str(r.get("publish_date", "")), r.get("title", ""))):
        try:
            _upsert_announcement(db, rec)
            count += 1
        except Exception as exc:
            logger.warning("announcement upsert failed: %s | %s", exc, rec.get("stock_code"))
    return count


def _upsert_announcement(db: Session, rec: dict) -> None:
    publish_date = _parse_date(rec.get("publish_date"))
    if not publish_date or not rec.get("stock_code") or not rec.get("title"):
        return

    uid = _compute_uid(rec.get("stock_code", "") + rec.get("title", "") + str(publish_date) + (rec.get("file_hash") or ""))

    existing = db.execute(
        select(AnnouncementHot).where(AnnouncementHot.announcement_uid == uid)
    ).scalar_one_or_none()

    fields = dict(
        stock_code=rec["stock_code"],
        title=rec["title"],
        publish_date=publish_date,
        announcement_type=rec.get("announcement_type"),
        content=rec.get("content"),
        summary_text=rec.get("summary_text"),
        key_fields_json=rec.get("key_fields_json"),
        source_url=rec.get("source_url"),
        file_path=rec.get("file_path"),
        file_type=rec.get("file_type"),
        original_filename=rec.get("original_filename"),
        file_hash=rec.get("file_hash"),
        vector_status="pending",
    )

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(AnnouncementHot(announcement_uid=uid, query_count=0, **fields))
    db.flush()


def _merge_research_report(db: Session, records: list[dict]) -> int:
    count = 0
    for rec in sorted(records, key=lambda r: (r.get("scope_type", ""), r.get("stock_code") or r.get("industry_code", ""), str(r.get("publish_date", "")))):
        try:
            _upsert_research_report(db, rec)
            count += 1
        except Exception as exc:
            logger.warning("research_report upsert failed: %s", exc)
    return count


def _upsert_research_report(db: Session, rec: dict) -> None:
    scope = rec.get("scope_type", "company")
    key = (rec.get("scope_type", "") + (rec.get("stock_code") or "") + (rec.get("industry_code") or "")
           + rec.get("title", "") + str(rec.get("publish_date", "")) + (rec.get("report_org") or "") + (rec.get("file_hash") or ""))
    uid = _compute_uid(key)

    existing = db.execute(
        select(ResearchReportHot).where(ResearchReportHot.report_uid == uid)
    ).scalar_one_or_none()

    fields = dict(
        scope_type=scope,
        stock_code=rec.get("stock_code"),
        industry_code=rec.get("industry_code"),
        title=rec.get("title", ""),
        publish_date=_parse_date(rec.get("publish_date")),
        report_org=rec.get("report_org"),
        content=rec.get("content"),
        summary_text=rec.get("summary_text"),
        source_type=rec.get("source_type"),
        source_url=rec.get("source_url"),
        file_path=rec.get("file_path"),
        file_type=rec.get("file_type"),
        original_filename=rec.get("original_filename"),
        file_hash=rec.get("file_hash"),
        vector_status="pending",
    )

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(ResearchReportHot(report_uid=uid, query_count=0, **fields))
    db.flush()


def _merge_news(db: Session, records: list[dict]) -> int:
    count = 0
    for rec in sorted(records, key=lambda r: (str(r.get("publish_time", "")), r.get("title", ""))):
        try:
            _upsert_news(db, rec)
            count += 1
        except Exception as exc:
            logger.warning("news upsert failed: %s", exc)
    return count


def _upsert_news(db: Session, rec: dict) -> None:
    uid = rec.get("news_uid") or _compute_uid(rec.get("source_url") or (rec.get("title", "") + str(rec.get("publish_time", ""))))

    existing = db.execute(
        select(NewsHot).where(NewsHot.news_uid == uid)
    ).scalar_one_or_none()

    fields = dict(
        title=rec.get("title", ""),
        publish_time=_parse_datetime(rec.get("publish_time")),
        source_name=rec.get("source_name"),
        source_url=rec.get("source_url"),
        news_type=rec.get("news_type"),
        content=rec.get("content"),
        summary_text=rec.get("summary_text"),
        related_stock_codes_json=rec.get("related_stock_codes_json"),
        related_industry_codes_json=rec.get("related_industry_codes_json"),
        file_path=rec.get("file_path"),
        file_type=rec.get("file_type"),
        original_filename=rec.get("original_filename"),
        file_hash=rec.get("file_hash"),
        vector_status="pending",
    )

    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(NewsHot(news_uid=uid, query_count=0, **fields))
    db.flush()


def _merge_macro(db: Session, records: list[dict]) -> int:
    count = 0
    for rec in records:
        try:
            existing = db.execute(
                select(MacroIndicator).where(
                    MacroIndicator.indicator_name == rec.get("indicator_name"),
                    MacroIndicator.period == rec.get("period"),
                )
            ).scalar_one_or_none()

            fields = dict(
                period_date=_parse_date(rec.get("period_date")),
                value=_decimal(rec.get("value")),
                unit=rec.get("unit"),
                category=rec.get("category"),
                summary_text=rec.get("summary_text"),
                source_type=rec.get("source_type"),
                source_url=rec.get("source_url"),
            )

            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
            else:
                db.add(MacroIndicator(
                    indicator_name=rec["indicator_name"],
                    period=rec["period"],
                    **fields,
                ))
            db.flush()
            count += 1
        except Exception as exc:
            logger.warning("macro upsert failed: %s", exc)
    return count


_MERGERS = {
    "financial": _merge_financial,
    "announcement": _merge_announcement,
    "research_report": _merge_research_report,
    "news": _merge_news,
    "macro": _merge_macro,
}


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _compute_uid(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:64]


def _parse_date(val: Any) -> date | None:
    if val is None:
        return None
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val)[:10])
    except Exception:
        return None


def _parse_datetime(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val).replace(" ", "T"))
    except Exception:
        return None


def _decimal(val: Any):
    if val is None:
        return None
    try:
        from decimal import Decimal
        return Decimal(str(val))
    except Exception:
        return None


def _get_dest_dir(data_type: str, rec: dict) -> Path:
    today = datetime.now()
    year = str(today.year)
    month = f"{today.month:02d}"

    if data_type == "financial":
        return RAW_FILES_ROOT / "financial_report" / year / rec.get("stock_code", "unknown")
    elif data_type == "announcement":
        return RAW_FILES_ROOT / "announcement" / year / rec.get("stock_code", "unknown")
    elif data_type == "research_report":
        scope = rec.get("scope_type", "company")
        if scope == "industry":
            return RAW_FILES_ROOT / "research_report" / "industry" / year / rec.get("industry_code", "unknown")
        return RAW_FILES_ROOT / "research_report" / "company" / year / rec.get("stock_code", "unknown")
    elif data_type == "news":
        return RAW_FILES_ROOT / "news" / year / month
    elif data_type == "macro":
        return RAW_FILES_ROOT / "macro" / year
    return RAW_FILES_ROOT / data_type / year


def _build_dest_filename(rec: dict, file_hash: str, suffix: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    code = rec.get("stock_code") or rec.get("industry_code") or "unknown"
    title = (rec.get("title") or rec.get("indicator_name") or "file")[:20]
    title = "".join(c for c in title if c.isalnum() or c in "-_")
    return f"{today}-{code}-{title}-{file_hash[:8]}{suffix}"
