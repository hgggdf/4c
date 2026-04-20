"""集中定义后端运行配置，并从 .env 文件中加载环境变量。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    tushare_token: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins(self) -> list[str]:
        """把逗号分隔的跨域来源字符串转换为 FastAPI 可直接使用的列表。"""
        return [item.strip() for item in self.allow_origins.split(",") if item.strip()]

    @property
    def database_url(self) -> str:
        """优先使用显式覆盖项，否则按 MySQL 配置动态拼接连接串。"""
        if self.database_url_override.strip():
            return self.database_url_override.strip()
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def sqlite_database_url(self) -> str:
        """构造 SQLite 兜底数据库连接串，并确保本地目录存在。"""
        database_path = Path(__file__).parent / self.local_database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{database_path.resolve().as_posix()}"


@lru_cache
def get_settings() -> Settings:
    """返回带缓存的配置实例，避免重复读取环境变量。"""
    return Settings()
