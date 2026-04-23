"""
ingest_jobs 模块
职责：
- 读取 manifest
- 校验 staging
- 调用 /api/ingest/* 或 /api/macro-write/*
- 记录结果
不负责抓取数据，不修改 crawler 代码
"""

from .config import IngestConfig, get_config
from .http_client import HttpClient, HttpResponse
from .validators import (
    ManifestValidator,
    StagingValidator,
    ValidationResult,
    validate_manifest,
    validate_staging,
    ALLOWED_DATA_CATEGORIES,
    CATEGORY_ENDPOINT_MAP,
    CATEGORY_STAGING_FILENAME,
)
from .loaders import (
    ManifestLoader,
    StagingLoader,
    IngestManifest,
    IngestJob,
    IngestJobBuilder,
)

__all__ = [
    "IngestConfig",
    "get_config",
    "HttpClient",
    "HttpResponse",
    "ManifestValidator",
    "StagingValidator",
    "ValidationResult",
    "validate_manifest",
    "validate_staging",
    "ALLOWED_DATA_CATEGORIES",
    "CATEGORY_ENDPOINT_MAP",
    "CATEGORY_STAGING_FILENAME",
    "ManifestLoader",
    "StagingLoader",
    "IngestManifest",
    "IngestJob",
    "IngestJobBuilder",
]
