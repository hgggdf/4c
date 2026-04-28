"""应用启动与健康检查入口。"""

from .runtime import check_database_health, init_application_database

__all__ = ["check_database_health", "init_application_database"]