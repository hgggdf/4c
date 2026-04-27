"""
Company Transformer
负责将 raw/company/ 下的公司主数据 JSON
转换为 staging/company_package.json

对应接口：/api/ingest/company-package
对应字段：company_master, company_profile, industries, company_industries
对应表：company_master / company_profile / industry_master / company_industry_map

company 链最复杂：
- master.json → company_master
- profile.json → company_profile
- industries.json → industries（行业主数据）
- company_industry_map.json → company_industries（公司-行业映射）
"""

from __future__ import annotations

import json
from pathlib import Path

from .base import BaseTransformer


class CompanyTransformer(BaseTransformer):
    DATA_CATEGORY = "company"
    STAGING_FILENAME = "company_package.json"
    TARGET_ENDPOINT = "/api/ingest/company-package"
    TARGET_TABLE = "company_master"
    INGEST_PACKAGE = "company-package"
    INGEST_FIELD = "company_master"

    def scan_raw(self, begin_date: str | None, end_date: str | None) -> list[Path]:
        """
        扫描 raw/company/ 下的所有文件
        company 链需要同时处理多个文件：master, profile, industries, company_industry_map
        """
        company_dir = self.raw_dir / "company"
        if not company_dir.exists():
            return []

        # 返回所有相关的 JSON 文件
        raw_files = []
        for fname in ("master.json", "profile.json", "industries.json", "company_industry_map.json"):
            fpath = company_dir / fname
            if fpath.exists():
                raw_files.append(fpath)

        return raw_files

    def load_raw(self, raw_path: Path) -> dict:
        """读取 raw 文件"""
        return json.loads(raw_path.read_text(encoding="utf-8"))

    def transform(self, raw_data: dict, raw_path: Path) -> list[dict]:
        """
        transform 对 company 链特殊：
        - 不是返回一个列表，而是组装完整的 company_package
        - 因此这里返回的是打包好的完整 payload（单条记录）
        """
        # company 链不走普通 transform 流程
        # 在 run() 中会调用 build_company_package() 代替
        return []

    def run(self, begin_date: str | None = None, end_date: str | None = None, dry_run: bool = False) -> dict:
        """
        company 链特殊处理：
        1. 扫描多个 raw 文件
        2. 组装完整 package
        3. 写入 staging
        4. 生成 manifest
        5. 生成 quality report
        """
        job_id = self._generate_job_id()
        company_dir = self.raw_dir / "company"

        # 加载所有 raw 文件
        master_data = self._load_optional(company_dir / "master.json")
        profile_data = self._load_optional(company_dir / "profile.json")
        industries_data = self._load_optional(company_dir / "industries.json")
        company_industry_map_data = self._load_optional(company_dir / "company_industry_map.json")

        # 检查是否有数据
        has_data = any([master_data, profile_data, industries_data, company_industry_map_data])
        if not has_data:
            return {
                "job_id": job_id,
                "data_category": self.DATA_CATEGORY,
                "status": "skipped",
                "reason": "no raw files found",
                "raw_count": 0,
                "staging_count": 0,
            }

        # 组装 package
        package = self.build_company_package(
            master_data=master_data,
            profile_data=profile_data,
            industries_data=industries_data,
            company_industry_map_data=company_industry_map_data,
        )

        if dry_run:
            record_count = 0
            if master_data:
                record_count = len(master_data.get("records", []))
            return {
                "job_id": job_id,
                "data_category": self.DATA_CATEGORY,
                "status": "dry_run",
                "dry_run": True,
                "raw_files_found": sum(1 for x in [master_data, profile_data, industries_data, company_industry_map_data] if x),
                "total_companies": record_count,
                "package_keys": list(package.get("payload", {}).keys()),
            }

        # 写入 staging
        staging_path = self.staging_dir / self.STAGING_FILENAME
        staging_count = self._write_staging_package(package, staging_path)

        # 计算 checksum
        checksum = self._sha256(staging_path)

        # 生成 manifest
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
            raw_files=[
                {"path": str(company_dir / "master.json"), "count": len(master_data.get("records", [])) if master_data else 0},
                {"path": str(company_dir / "profile.json"), "count": len(profile_data.get("records", [])) if profile_data else 0},
                {"path": str(company_dir / "industries.json"), "count": len(industries_data.get("records", [])) if industries_data else 0},
            ],
            staging_count=staging_count,
            errors=[],
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
            "raw_count": sum(1 for x in [master_data, profile_data, industries_data, company_industry_map_data] if x),
            "staging_count": staging_count,
            "errors": [],
        }

    def build_company_package(
        self,
        master_data: dict | None,
        profile_data: dict | None,
        industries_data: dict | None,
        company_industry_map_data: dict | None,
    ) -> dict:
        """
        组装完整的 company_package
        返回格式：
        {
          "generated_at": "...",
          "payload": {
            "company_master": {...},
            "company_profile": {...},
            "industries": [...],
            "company_industries": [...]
          }
        }
        """
        from datetime import datetime, timezone

        # company_master
        company_master = None
        if master_data:
            records = master_data.get("records", [])
            if records:
                first = records[0]
                company_master = {
                    "stock_code": first.get("stock_code"),
                    "stock_name": first.get("stock_name"),
                    "full_name": first.get("full_name"),
                    "exchange": first.get("exchange"),
                    "industry_level1": first.get("industry_level1"),
                    "industry_level2": first.get("industry_level2"),
                    "listing_date": self._normalize_date(first.get("listing_date")),
                    "status": first.get("status", "active"),
                    "source_type": first.get("source_type", "multi_source"),
                    "source_url": first.get("source_url"),
                }

        # company_profile
        company_profile = None
        if profile_data:
            records = profile_data.get("records", [])
            if records:
                first = records[0]
                company_profile = {
                    "stock_code": first.get("stock_code"),
                    "business_summary": first.get("business_summary"),
                    "core_products_json": first.get("core_products_json"),
                    "main_segments_json": first.get("main_segments_json"),
                    "market_position": first.get("market_position"),
                    "management_summary": first.get("management_summary"),
                }

        # industries
        industries = []
        if industries_data:
            for record in industries_data.get("records", []):
                industries.append({
                    "industry_code": record.get("industry_code"),
                    "industry_name": record.get("industry_name"),
                    "parent_industry_code": record.get("parent_industry_code"),
                    "industry_level": record.get("industry_level", 1),
                    "description": record.get("description"),
                })

        # company_industries
        company_industries = []
        if company_industry_map_data:
            for record in company_industry_map_data.get("records", []):
                company_industries.append({
                    "stock_code": record.get("stock_code"),
                    "industry_code": record.get("industry_code"),
                    "is_primary": record.get("is_primary", 1),
                })

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "company_master": company_master,
                "company_profile": company_profile,
                "industries": industries,
                "company_industries": company_industries,
            },
        }

    def _write_staging_package(self, package: dict, staging_path: Path) -> int:
        """写入 staging 文件"""
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        staging_path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
        # 返回 company_master 计数
        master = package.get("payload", {}).get("company_master")
        return 1 if master else 0

    def build_manifest(self, job_id: str, staging_path: Path, staging_count: int,
                       checksum: str, begin_date: str | None, end_date: str | None) -> dict:
        """构建 manifest"""
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

    # ─────────────────────────────────────────────────────────
    # 工具方法
    # ─────────────────────────────────────────────────────────

    def _load_optional(self, path: Path) -> dict | None:
        """可选地加载 JSON 文件，不存在则返回 None"""
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return None

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
