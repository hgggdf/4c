from app.service.database_service import DatabaseService


def init_database() -> None:
    DatabaseService().initialize_database()


def check_db_health() -> dict:
    return DatabaseService().check_health()
