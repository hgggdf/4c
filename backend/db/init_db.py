"""数据库初始化兼容入口，对外暴露初始化与健康检查函数。"""

from app.service.database_service import DatabaseService


def init_database() -> None:
    """调用数据库服务执行建表和初始化数据导入。"""
    DatabaseService().initialize_database()


def check_db_health() -> dict:
    """调用数据库服务返回数据库健康状态。"""
    return DatabaseService().check_health()
