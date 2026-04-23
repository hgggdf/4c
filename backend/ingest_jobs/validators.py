"""
校验器
负责校验 manifest 和 staging 文件的合法性
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# 允许的 data_category 枚举
ALLOWED_DATA_CATEGORIES = {
    "company",
    "stock_daily",
    "announcement_raw",
    "research_report",
    "macro",
    "patent",
}

# data_category → target.endpoint 映射（"NONE" 表示禁止入库）
CATEGORY_ENDPOINT_MAP = {
    "company": "/api/ingest/company-package",
    "stock_daily": "/api/ingest/financial-package",
    "announcement_raw": "/api/ingest/announcement-package",
    "research_report": "/api/ingest/news-package",
    "macro": "/api/macro-write/macro-indicators",
    "patent": "NONE",
}

# data_category → staging 文件名
CATEGORY_STAGING_FILENAME = {
    "company": "company_package.json",
    "stock_daily": "stock_daily_package.json",
    "announcement_raw": "announcement_package.json",
    "research_report": "research_reports_phasec_live/research_reports_latest.json",
    "macro": "macro_phasec_live/macro_indicators_latest.json",
    "patent": "patent_phasec_live/patents_latest.json",
}

# 必填字段（data_category → 必填字段列表）
REQUIRED_FIELDS = {
    "company": [],
    "stock_daily": ["stock_code", "trade_date"],
    "announcement_raw": ["stock_code", "title", "publish_date"],
    "research_report": ["title", "publish_time"],
    "macro": ["indicator_name", "period", "value"],
    "patent": ["company_name"],
}


@dataclass
class ValidationResult:
    """校验结果"""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.valid

    def add_error(self, msg: str):
        self.errors.append(msg)
        self.valid = False

    def add_warning(self, msg: str):
        self.warnings.append(msg)


class ManifestValidator:
    """校验 manifest 文件"""

    def __init__(self, backend_root: str | None = None):
        if backend_root is None:
            backend_root = Path(__file__).resolve().parents[1].as_posix()
        self.backend_root = Path(backend_root)

    def validate(self, manifest_path: str | Path | dict) -> ValidationResult:
        """
        校验 manifest 文件
        检查：
        1. 文件存在
        2. JSON 合法
        3. spec_version = "1.0"
        4. staging_path 存在
        5. staging_sha256 匹配
        6. data_category 合法
        7. target.endpoint 与 data_category 匹配
        8. patent 禁止入库

        manifest_path 可以是：
        - 文件路径（str 或 Path）：从文件读取 JSON
        - dict：直接校验 dict
        """
        result = ValidationResult(valid=True)

        # 判断是 dict 还是文件路径
        if isinstance(manifest_path, dict):
            manifest = manifest_path
        else:
            manifest_path = Path(manifest_path)
            # 1. 文件存在
            if not manifest_path.exists():
                result.add_error(f"manifest 不存在: {manifest_path}")
                return result
            # 2. JSON 合法
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception as exc:
                result.add_error(f"manifest JSON 解析失败: {exc}")
                return result

        # 3. spec_version
        spec_version = manifest.get("spec_version")
        if spec_version != "1.0":
            result.add_error(f"spec_version 应为 '1.0'，实际: {spec_version}")

        # 8. staging_format_version（新增，必需）
        staging_format_version = manifest.get("staging_format_version")
        if staging_format_version is None:
            result.add_error("manifest 缺少 staging_format_version 字段")
        elif staging_format_version != "1.0":
            result.add_error(f"staging_format_version 应为 '1.0'，实际: {staging_format_version}")

        # 4. data_category 合法性
        data_category = manifest.get("data_category")
        if data_category not in ALLOWED_DATA_CATEGORIES:
            result.add_error(f"data_category 不合法: {data_category}，允许: {ALLOWED_DATA_CATEGORIES}")

        # 6. target.endpoint 匹配
        if data_category in CATEGORY_ENDPOINT_MAP:
            expected_endpoint = CATEGORY_ENDPOINT_MAP[data_category]
            actual_endpoint = manifest.get("target", {}).get("endpoint")
            if actual_endpoint != expected_endpoint:
                result.add_error(
                    f"target.endpoint 不匹配: expected={expected_endpoint}, actual={actual_endpoint}"
                )

        # 7. patent 禁止入库
        if data_category == "patent":
            endpoint = manifest.get("target", {}).get("endpoint")
            if endpoint != "NONE":
                result.add_error(f"patent 的 target.endpoint 必须为 'NONE'，实际: {endpoint}")

        # 5. staging_path 存在
        staging_rel = manifest.get("files", {}).get("staging_path")
        if staging_rel:
            staging_path = self.backend_root / staging_rel
            if not staging_path.exists():
                result.add_error(f"staging 文件不存在: {staging_path}")

        # 5. staging_sha256 匹配
        stored_sha256 = manifest.get("checksum", {}).get("staging_sha256")
        if staging_rel and stored_sha256 and staging_path.exists():
            actual_sha256 = self._sha256(staging_path)
            if actual_sha256 != stored_sha256:
                result.add_error(
                    f"staging SHA256 不匹配: manifest={stored_sha256[:8]}..., actual={actual_sha256[:8]}..."
                )

        # status 必须是 ready
        status = manifest.get("status")
        if status not in ("ready", "ingesting"):
            result.add_warning(f"manifest status 为 '{status}'，通常应为 'ready'")

        return result

    def _sha256(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()


class StagingValidator:
    """校验 staging 文件内容"""

    def __init__(self):
        pass

    def validate(self, staging_data: dict, data_category: str) -> ValidationResult:
        """
        校验 staging 内容
        检查：
        1. 必填字段存在
        2. 记录列表不为空
        3. 每条记录必填字段完整
        """
        result = ValidationResult(valid=True)

        # 获取 payload
        if data_category in ("macro", "patent"):
            # macro 和 patent 顶层是 records
            records = staging_data.get("records", [])
        else:
            # 其他是 payload.xxx
            payload = staging_data.get("payload", {})
            # 对 company，取 company_master
            if data_category == "company":
                company_master = payload.get("company_master", {})
                records = [company_master] if company_master else []
            # stock_daily, announcement, research_report 取对应字段
            else:
                field_map = {
                    "stock_daily": "stock_daily",
                    "announcement_raw": "raw_announcements",
                    "research_report": "news_raw",
                }
                records = payload.get(field_map.get(data_category, ""), [])

        # 检查记录数
        if not records:
            result.add_warning("staging 记录列表为空")

        # 检查必填字段
        required_fields = REQUIRED_FIELDS.get(data_category, [])
        for i, record in enumerate(records):
            for field_name in required_fields:
                if not record.get(field_name):
                    result.add_error(
                        f"第 {i+1} 条记录缺少必填字段 '{field_name}'"
                    )

        return result


def validate_manifest(manifest_path: str | Path, backend_root: str | None = None) -> ValidationResult:
    """便捷函数：校验 manifest"""
    validator = ManifestValidator(backend_root=backend_root)
    return validator.validate(manifest_path)


def validate_staging(staging_data: dict, data_category: str) -> ValidationResult:
    """便捷函数：校验 staging"""
    validator = StagingValidator()
    return validator.validate(staging_data, data_category)
