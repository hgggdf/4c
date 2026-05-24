"""
Patent Transformer
负责将 raw/patents/cnipa/ 下的专利 JSON
转换为 staging/patent_phasec_live/patents_latest.json

注意：专利当前没有对应的 ingest 接口
因此：
- 生成 raw（已有）
- 生成 staging（已有）
- 生成 manifest（endpoint = "NONE"）
- 生成 quality_report
- 但不生成任何可入库的 payload

data_category="patent" 时，ingest_jobs 会直接跳过
"""

from __future__ import annotations

import json
from pathlib import Path

from .base import BaseTransformer


class PatentTransformer(BaseTransformer):
    DATA_CATEGORY = "patent"
    STAGING_FILENAME = "patent_phasec_live/patents_latest.json"
    TARGET_ENDPOINT = "NONE"  # 禁止入库
    TARGET_TABLE = "NONE"
    INGEST_PACKAGE = "NONE"
    INGEST_FIELD = "NONE"

    def scan_raw(self, begin_date: str | None, end_date: str | None) -> list[Path]:
        """
        扫描 raw/patents/cnipa/ 下的专利文件
        """
        patents_dir = self.raw_dir / "patents" / "cnipa"
        if not patents_dir.exists():
            return []

        raw_files = list(patents_dir.glob("patents_*.json"))

        # 按日期过滤
        if begin_date or end_date:
            filtered = []
            for f in raw_files:
                parts = f.stem.split("_")
                if len(parts) >= 2:
                    file_date = parts[-1]  # patents_2026-04-23.json
                    if begin_date and file_date < begin_date:
                        continue
                    if end_date and file_date > end_date:
                        continue
                filtered.append(f)
            raw_files = filtered

        return sorted(raw_files)

    def load_raw(self, raw_path: Path) -> dict:
        """读取 raw 文件"""
        return json.loads(raw_path.read_text(encoding="utf-8"))

    def transform(self, raw_data: dict, raw_path: Path) -> list[dict]:
        """
        专利 staging 格式（规范要求）：
        {
          "generated_at": "...",
          "records": [
            {
              "stock_code": "600276",
              "company_name": "江苏恒瑞医药股份有限公司",
              "patent_title": "一种...",
              "patent_type": "发明专利",
              "application_no": "CN2026XXXX",
              "publication_no": "CN11XXXX",
              "application_date": "2026-04-01",
              "publication_date": "2026-04-20",
              "legal_status": "公开",
              "source_type": "cnipa",
              "source_url": "https://....",
              "fetched_at": "2026-04-23T12:00:00"
            }
          ]
        }
        """
        records = raw_data.get("records", [])

        result = []
        for item in records:
            # 跳过无效记录
            company_name = item.get("company_name") or item.get("applicant", "")
            patent_title = item.get("patent_title") or item.get("title", "")
            if not company_name and not patent_title:
                continue

            result.append({
                "stock_code": item.get("stock_code"),
                "company_name": company_name,
                "patent_title": patent_title,
                "patent_type": item.get("patent_type"),
                "application_no": item.get("application_no") or item.get("application_number"),
                "publication_no": item.get("publication_no") or item.get("publication_number"),
                "application_date": self._normalize_date(item.get("application_date")),
                "publication_date": self._normalize_date(item.get("publication_date")),
                "legal_status": item.get("legal_status"),
                "source_type": item.get("source_type", "cnipa"),
                "source_url": item.get("source_url"),
                "fetched_at": item.get("fetched_at"),
            })

        return result

    def run(self, begin_date: str | None = None, end_date: str | None = None, dry_run: bool = False) -> dict:
        """
        patent 链特殊处理：
        - 生成 staging 文件
        - 生成 manifest（endpoint = "NONE"）
        - 生成 quality_report
        - 但标记为不可入库
        """
        job_id = self._generate_job_id()

        # 扫描 raw 文件
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

        # 读取并转换所有专利文件
        all_records = []
        raw_file_info = []
        errors = []

        for raw_path in raw_files:
            try:
                raw_data = self.load_raw(raw_path)
                records = self.transform(raw_data, raw_path)
                all_records.extend(records)
                raw_file_info.append({"path": str(raw_path), "count": len(records)})
            except Exception as exc:
                errors.append({"file": str(raw_path), "error": str(exc)})

        if dry_run:
            return {
                "job_id": job_id,
                "data_category": self.DATA_CATEGORY,
                "status": "dry_run",
                "dry_run": True,
                "raw_files_found": len(raw_files),
                "total_records": len(all_records),
                "errors": errors,
            }

        # 写入 staging
        staging_path = self.staging_dir / self.STAGING_FILENAME
        staging_count = self.write_staging(all_records, staging_path)

        # 计算 checksum
        checksum = self._sha256(staging_path)

        # 生成 manifest（endpoint = "NONE"，明确禁止入库）
        manifest = self.build_manifest(
            job_id=job_id,
            staging_path=staging_path,
            staging_count=staging_count,
            checksum=checksum,
            begin_date=begin_date,
            end_date=end_date,
        )
        self.write_manifest(manifest)

        # 生成 quality report
        quality_report = self.build_quality_report(
            job_id=job_id,
            raw_files=raw_file_info,
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
            "raw_count": len(raw_files),
            "staging_count": staging_count,
            "ingest_allowed": False,  # 专利禁止入库
            "errors": errors,
        }

    def write_staging(self, records: list[dict], staging_path: Path) -> int:
        """写入 staging 文件（专利格式：顶层是 records）"""
        staging_path.parent.mkdir(parents=True, exist_ok=True)
        from datetime import datetime, timezone
        staging_obj = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "records": records,
        }
        staging_path.write_text(json.dumps(staging_obj, ensure_ascii=False, indent=2), encoding="utf-8")
        return len(records)

    def build_manifest(self, job_id: str, staging_path: Path, staging_count: int,
                       checksum: str, begin_date: str | None, end_date: str | None) -> dict:
        """专利 manifest：endpoint = NONE，明确禁止入库"""
        raw_rel = str(staging_path).replace(str(self.backend_root) + "/", "")
        return {
            "spec_version": self.SPEC_VERSION,
            "staging_format_version": "1.0",
            "job_id": job_id,
            "created_at": self._now_iso(),
            "producer": {
                "system": "openclaw",
                "module": self.__class__.__name__,
                "run_id": job_id,
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
                "ingest_allowed": False,
            },
            "files": {
                "staging_path": raw_rel,
            },
            "record_stats": {
                "staging_count": staging_count,
                "expected_write_count": 0,  # 专利不入库
            },
            "checksum": {
                "staging_sha256": checksum,
            },
            "status": "ready",
        }

    # ─────────────────────────────────────────────────────────
    # 工具方法
    # ─────────────────────────────────────────────────────────

    def _normalize_date(self, value) -> str | None:
        """标准化日期为 YYYY-MM-DD"""
        if not value:
            return None
        text = str(value).strip()
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            return text
        if len(text) == 8 and text.isdigit():
            return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
        return None

    def _now_iso(self) -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
