"""
Transform 基类
定义 raw 读取、staging 写入、manifest 生成的标准流程
"""

from __future__ import annotations

import hashlib
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path


class BaseTransformer(ABC):
    """
    所有 Transformer 的基类，定义标准流程：

    1. scan_raw()     → 扫描 raw 目录下待处理的文件
    2. load_raw()     → 读取原始 JSON
    3. transform()    → 转换为标准 staging 格式
    4. write_staging()→ 写入 staging 目录
    5. write_manifest()→ 生成 manifest JSON
    6. write_quality_report() → 生成质量报告
    """

    # 子类必须覆盖
    DATA_CATEGORY: str = ""
    STAGING_FILENAME: str = ""
    TARGET_ENDPOINT: str = ""
    TARGET_TABLE: str = ""
    INGEST_PACKAGE: str = ""
    INGEST_FIELD: str = ""

    # 固定值
    SPEC_VERSION = "1.0"

    def __init__(self, backend_root: str | None = None):
        """
        backend_root: 指向 backend/ 目录的绝对路径
                      默认从本文件位置推断
        """
        if backend_root is None:
            backend_root = Path(__file__).resolve().parents[2].as_posix()
        self.backend_root = Path(backend_root)
        self.raw_dir = self.backend_root / "crawler" / "raw"
        self.staging_dir = self.backend_root / "crawler" / "staging"
        self.manifests_dir = self.backend_root / "ingest_jobs" / "manifests"
        self.quality_reports_dir = self.staging_dir / "quality_reports"

    # ─────────────────────────────────────────────────────────
    # 公开入口
    # ─────────────────────────────────────────────────────────

    def run(self, begin_date: str | None = None, end_date: str | None = None, dry_run: bool = False) -> dict:
        """
        执行完整 transform 流程
        返回结果摘要
        """
        job_id = self._generate_job_id()

        # 1. 扫描 raw 文件
        raw_files = self.scan_raw(begin_date, end_date)
        if not raw_files:
            return {
                "job_id": job_id,
                "data_category": self.DATA_CATEGORY,
                "status": "skipped",
                "reason": "no raw files found",
                "raw_count": 0,
                "staging_count": 0,
            }

        # 2. 读取并转换
        all_records = []
        all_raw_records = []
        errors = []

        for raw_path in raw_files:
            try:
                raw_data = self.load_raw(raw_path)
                records = self.transform(raw_data, raw_path)
                all_records.extend(records)
                all_raw_records.append({"path": str(raw_path), "count": len(records)})
            except Exception as exc:
                errors.append({"file": str(raw_path), "error": str(exc)})

        if dry_run:
            return {
                "job_id": job_id,
                "data_category": self.DATA_CATEGORY,
                "status": "dry_run",
                "raw_files_found": len(raw_files),
                "raw_files_processed": len(all_raw_records),
                "total_records": len(all_records),
                "errors": errors,
                "dry_run": True,
            }

        # 3. 写入 staging
        staging_path = self.staging_dir / self.STAGING_FILENAME
        staging_count = self.write_staging(all_records, staging_path)

        # 4. 计算 checksum
        checksum = self._sha256(staging_path)

        # 5. 生成 manifest
        manifest = self.build_manifest(
            job_id=job_id,
            staging_path=staging_path,
            staging_count=staging_count,
            checksum=checksum,
            begin_date=begin_date,
            end_date=end_date,
        )
        self.write_manifest(manifest)

        # 6. 生成 quality report
        quality_report = self.build_quality_report(
            job_id=job_id,
            raw_files=all_raw_records,
            staging_count=staging_count,
            errors=errors,
            staging_path=staging_path,
        )
        self.write_quality_report(quality_report)

        return {
            "job_id": job_id,
            "data_category": self.DATA_CATEGORY,
            "status": "done",
            "staging_path": str(staging_path),
            "manifest_path": str(self.manifests_dir / f"{job_id}.json"),
            "quality_report_path": str(self.quality_reports_dir / f"{job_id}_quality_report.json"),
            "raw_count": len(all_raw_records),
            "staging_count": staging_count,
            "errors": errors,
        }

    # ─────────────────────────────────────────────────────────
    # 子类必须实现的抽象方法
    # ─────────────────────────────────────────────────────────

    @abstractmethod
    def scan_raw(self, begin_date: str | None, end_date: str | None) -> list[Path]:
        """
        扫描 raw 目录，返回待处理的文件列表
        按 begin_date/end_date 过滤（如果适用）
        """
        ...

    @abstractmethod
    def load_raw(self, raw_path: Path) -> dict:
        """读取单个 raw 文件，返回解析后的 dict"""
        ...

    @abstractmethod
    def transform(self, raw_data: dict, raw_path: Path) -> list[dict]:
        """
        将 raw_data 转换为标准 staging 记录列表
        返回的是 payload 中对应字段的列表（如 stock_daily 列表）
        """
        ...

    # ─────────────────────────────────────────────────────────
    # 通用方法（可覆盖）
    # ─────────────────────────────────────────────────────────

    def write_staging(self, records: list[dict], staging_path: Path) -> int:
        """写入 staging 文件"""
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        payload = self.build_staging_payload(records)
        staging_obj = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        staging_path.write_text(json.dumps(staging_obj, ensure_ascii=False, indent=2), encoding="utf-8")
        return len(records)

    def build_staging_payload(self, records: list[dict]) -> dict:
        """
        构建 staging payload
        子类覆盖以返回正确的结构
        """
        raise NotImplementedError

    def build_manifest(
        self,
        job_id: str,
        staging_path: Path,
        staging_count: int,
        checksum: str,
        begin_date: str | None,
        end_date: str | None,
    ) -> dict:
        """构建 manifest 对象"""
        raw_rel = str(staging_path).replace(str(self.backend_root) + "/", "")
        run_parts = job_id.split("_")
        run_uid = run_parts[1] if len(run_parts) > 1 else "unknown"
        run_seq = run_parts[2] if len(run_parts) > 2 else "unknown"
        return {
            "spec_version": self.SPEC_VERSION,
            "staging_format_version": "1.0",
            "job_id": job_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "producer": {
                "system": "openclaw",
                "module": self.__class__.__name__,
                "run_id": f"run_{run_uid}_{run_seq}",
            },
            "data_category": self.DATA_CATEGORY,
            "time_window": {
                "begin_date": begin_date,
                "end_date": end_date,
            },
            "target": {
                "endpoint": self.TARGET_ENDPOINT,
                "ingest_package": self.INGEST_PACKAGE,
                "ingest_field": self.INGEST_FIELD,
                "target_table": self.TARGET_TABLE,
            },
            "files": {
                "staging_path": raw_rel,
            },
            "record_stats": {
                "staging_count": staging_count,
                "expected_write_count": staging_count,
            },
            "checksum": {
                "staging_sha256": checksum,
            },
            "status": "ready",
        }

    def build_quality_report(
        self,
        job_id: str,
        raw_files: list[dict],
        staging_count: int,
        errors: list[dict],
        staging_path: Path,
    ) -> dict:
        """构建质量报告"""
        return {
            "report_id": f"{job_id}_quality",
            "job_id": job_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_category": self.DATA_CATEGORY,
            "staging_format_version": "1.0",
            "summary": {
                "total_raw_files": len(raw_files),
                "total_staging_records": staging_count,
                "error_count": len(errors),
            },
            "raw_files": raw_files,
            "staging_path": str(staging_path),
            "errors": errors,
            "validation": {
                "staging_exists": staging_path.exists(),
                "staging_readable": self._is_valid_json(staging_path),
            },
        }

    def write_manifest(self, manifest: dict) -> None:
        """写入 manifest 文件"""
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        path = self.manifests_dir / f"{manifest['job_id']}.json"
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def write_quality_report(self, report: dict) -> None:
        """写入 quality report 文件"""
        self.quality_reports_dir.mkdir(parents=True, exist_ok=True)
        path = self.quality_reports_dir / f"{report['job_id']}_quality_report.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # ─────────────────────────────────────────────────────────
    # 工具方法
    # ─────────────────────────────────────────────────────────

    def _generate_job_id(self) -> str:
        """生成唯一 job_id"""
        now = datetime.now(timezone.utc)
        uid = uuid.uuid4().hex[:6]
        return f"openclaw_{now.strftime('%Y%m%d')}_{uid}"

    def _sha256(self, path: Path) -> str:
        """计算文件 sha256"""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _is_valid_json(self, path: Path) -> bool:
        """检查文件是否为有效 JSON"""
        try:
            json.loads(path.read_text(encoding="utf-8"))
            return True
        except Exception:
            return False
