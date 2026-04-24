"""集中定义后端运行配置，并从 .env 文件中加载环境变量。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


_CONFIG_DIR = Path(__file__).resolve().parent
ENV_FILE = _CONFIG_DIR / ".env"
ROOT_ENV_FILE = _CONFIG_DIR.parent / ".env"

if not ENV_FILE.exists() and ROOT_ENV_FILE.exists():
    ENV_FILE = ROOT_ENV_FILE


class Settings(BaseSettings):
    """封装应用运行时需要的基础配置、数据库配置和第三方服务配置。"""

    app_name: str = "Stock Agent API"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    allow_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "123456"
    mysql_database: str = "stock_agent"

    demo_user_id: int = 1
    demo_username: str = "demo_user"

    database_url_override: str = ""
    local_database_path: str = "local_data/stock_agent.db"

    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com"
    claude_model: str = "claude-sonnet-4-6"
    glm_api_key: str = ""
    glm_base_url: str = ""
    glm_model: str = ""
    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.ai/v1"
    kimi_model: str = "moonshot-v1-8k"
    tushare_token: str = ""

    crawler_enable_playwright_fallback: bool = False
    crawler_retry_times: int = 3
    crawler_backoff_base: float = 0.8
    crawler_min_delay: float = 0.6
    crawler_max_delay: float = 1.5
    crawler_use_random_ua: bool = True
    crawler_source_mode: str = "auto"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins(self) -> list[str]:
        """把逗号分隔的跨域来源字符串转换为 FastAPI 可直接使用的列表。"""
        return [item.strip() for item in self.allow_origins.split(",") if item.strip()]

    @property
    def database_url(self) -> str:
        """返回运行主链使用的 MySQL 连接串。"""
        if self.database_url_override.strip():
            database_url = self.database_url_override.strip()
            self._ensure_mysql_url(database_url, source="DATABASE_URL_OVERRIDE")
            return database_url
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def sqlite_database_url(self) -> str:
        """保留给测试或手工迁移使用，不会在运行主链自动启用。"""
        database_path = Path(__file__).parent / self.local_database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{database_path.resolve().as_posix()}"

    def _ensure_mysql_url(self, database_url: str, *, source: str) -> None:
        """确保显式覆盖项仍然指向 MySQL，而不是 SQLite 等其他方言。"""
        try:
            backend_name = make_url(database_url).get_backend_name()
        except Exception as exc:  # noqa: BLE001
            raise ValueError(
                f"{source} 配置无效。当前运行模式只支持 MySQL。"
            ) from exc
        if backend_name != "mysql":
            raise ValueError(
                f"{source} 必须是 MySQL 连接串。当前运行模式只支持 MySQL。"
            )


@lru_cache
def get_settings() -> Settings:
    """返回带缓存的配置实例，避免重复读取环境变量。"""
    return Settings()
