"""
ingest_jobs 配置模块
从 backend/.env 读取配置，或使用默认值
"""

from __future__ import annotations

from pathlib import Path


class IngestConfig:
    """ingest_jobs 运行配置"""

    def __init__(self, backend_root: str | None = None):
        """
        backend_root: 指向 backend/ 目录的绝对路径
        """
        if backend_root is None:
            backend_root = Path(__file__).resolve().parents[1].as_posix()
        self.backend_root = Path(backend_root)

        # 读取 .env（如果存在）
        self._load_env()

        # API 配置
        self.api_base_url = getattr(self, "_api_base_url", "http://127.0.0.1:8000")
        self.api_timeout = getattr(self, "_api_timeout", 30)
        self.api_retry_times = getattr(self, "_api_retry_times", 3)

        # 目录路径
        self.ingest_jobs_dir = self.backend_root / "ingest_jobs"
        self.manifests_dir = self.ingest_jobs_dir / "manifests"
        self.staging_dir = self.backend_root / "crawler" / "staging"

        # 并发配置
        self.max_workers = getattr(self, "_max_workers", 4)

    def _load_env(self):
        """从 .env 加载配置"""
        env_file = self.backend_root / ".env"
        if not env_file.exists():
            return

        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            if key == "API_BASE_URL":
                self._api_base_url = value
            elif key == "API_TIMEOUT":
                self._api_timeout = int(value)
            elif key == "API_RETRY_TIMES":
                self._api_retry_times = int(value)
            elif key == "MAX_WORKERS":
                self._max_workers = int(value)

    def api_url(self, endpoint: str) -> str:
        """拼接完整 API URL"""
        base = self.api_base_url.rstrip("/")
        endpoint = endpoint.lstrip("/")
        return f"{base}/{endpoint}"


# 全局单例
_config: IngestConfig | None = None


def get_config(backend_root: str | None = None) -> IngestConfig:
    """获取配置单例"""
    global _config
    if _config is None or backend_root is not None:
        _config = IngestConfig(backend_root=backend_root)
    return _config
