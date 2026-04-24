"""
加载器
负责读取 manifest 和 staging 文件
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class IngestManifest:
    """manifest 封装"""
    job_id: str
    data_category: str
    target_endpoint: str
    target_table: str
    staging_path: str  # 相对路径
    staging_count: int
    checksum: str
    status: str
    raw_manifest: dict = field(default_factory=dict)

    @property
    def ingest_allowed(self) -> bool:
        """是否允许入库（patent 禁止）"""
        return self.data_category != "patent" and self.target_endpoint != "NONE"

    @property
    def staging_abs_path(self) -> Path:
        """返回 staging 绝对路径（需结合 backend_root）"""
        return Path(self.staging_path)


@dataclass
class IngestJob:
    """一条 ingest 任务"""
    manifest: IngestManifest
    staging_data: dict
    success_count: int = 0
    failed_count: int = 0
    error_message: str | None = None


class ManifestLoader:
    """读取并解析 manifest 文件"""

    def __init__(self, backend_root: str | None = None):
        if backend_root is None:
            backend_root = Path(__file__).resolve().parents[1].as_posix()
        self.backend_root = Path(backend_root)
        self.manifests_dir = self.backend_root / "ingest_jobs" / "manifests"

    def load(self, job_id: str) -> IngestManifest | None:
        """
        按 job_id 加载 manifest
        """
        manifest_path = self.manifests_dir / f"{job_id}.json"
        return self._load_from_path(manifest_path)

    def load_from_path(self, manifest_path: str | Path) -> IngestManifest | None:
        """
        从指定路径加载 manifest
        """
        return self._load_from_path(Path(manifest_path))

    def _load_from_path(self, manifest_path: Path) -> IngestManifest | None:
        """内部：解析 manifest 文件"""
        if not manifest_path.exists():
            return None

        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return None

        return IngestManifest(
            job_id=raw.get("job_id", ""),
            data_category=raw.get("data_category", ""),
            target_endpoint=raw.get("target", {}).get("endpoint", ""),
            target_table=raw.get("target", {}).get("target_table", ""),
            staging_path=raw.get("files", {}).get("staging_path", ""),
            staging_count=raw.get("record_stats", {}).get("expected_write_count", 0),
            checksum=raw.get("checksum", {}).get("staging_sha256", ""),
            status=raw.get("status", "unknown"),
            raw_manifest=raw,
        )

    def list_manifests(self, data_category: str | None = None) -> list[IngestManifest]:
        """
        列出所有 manifest
        可按 data_category 过滤
        """
        if not self.manifests_dir.exists():
            return []

        manifests = []
        for f in self.manifests_dir.glob("openclaw_*.json"):
            manifest = self._load_from_path(f)
            if manifest is None:
                continue
            if data_category and manifest.data_category != data_category:
                continue
            manifests.append(manifest)

        # 按时间倒序
        manifests.sort(key=lambda m: m.job_id, reverse=True)
        return manifests

    def list_pending_manifests(self) -> list[IngestManifest]:
        """列出所有 status=ready 的 manifest（待处理）"""
        all_manifests = self.list_manifests()
        return [m for m in all_manifests if m.status == "ready"]


class StagingLoader:
    """读取 staging 文件"""

    def __init__(self, backend_root: str | None = None):
        if backend_root is None:
            backend_root = Path(__file__).resolve().parents[1].as_posix()
        self.backend_root = Path(backend_root)

    def load(self, staging_path: str | Path) -> dict | None:
        """
        读取 staging JSON
        staging_path 可以是绝对路径或相对路径（相对于 backend_root）
        """
        if not Path(staging_path).is_absolute():
            staging_path = self.backend_root / staging_path

        staging_path = Path(staging_path)
        if not staging_path.exists():
            return None

        try:
            return json.loads(staging_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def load_for_manifest(self, manifest: IngestManifest) -> dict | None:
        """根据 manifest 加载对应的 staging"""
        staging_path = self.backend_root / manifest.staging_path
        return self.load(staging_path)


class IngestJobBuilder:
    """
    根据 manifest 构建完整的 IngestJob
    """

    def __init__(self, backend_root: str | None = None):
        self.manifest_loader = ManifestLoader(backend_root=backend_root)
        self.staging_loader = StagingLoader(backend_root=backend_root)

    def build(self, job_id: str) -> IngestJob | None:
        """
        加载 manifest + staging，返回完整的 IngestJob
        """
        manifest = self.manifest_loader.load(job_id)
        if manifest is None:
            return None

        staging_data = self.staging_loader.load_for_manifest(manifest)
        if staging_data is None:
            return None

        return IngestJob(
            manifest=manifest,
            staging_data=staging_data,
        )

    def build_from_manifest(self, manifest: IngestManifest) -> IngestJob | None:
        """直接用 manifest 对象构建 IngestJob"""
        staging_data = self.staging_loader.load_for_manifest(manifest)
        if staging_data is None:
            return None

        return IngestJob(
            manifest=manifest,
            staging_data=staging_data,
        )
