"""公司资料存储门面，兼容旧调用方式并转发到新的 CompanyService。"""

from db.session import SessionLocal
from app.data.local_company_dataset_store import LocalCompanyDataStore
from app.service.company_service import CompanyService


class CompanyDataStore:
    """为脚本或旧代码提供无感知的公司资料读写接口。"""

    def __init__(self) -> None:
        self.local_store = LocalCompanyDataStore()
        self.company_service = CompanyService()

    def load_company_dataset(self, symbol: str, compact: bool = False) -> dict | None:
        with SessionLocal() as db:
            return self.company_service.load_company_dataset(db, symbol, compact=compact)

    def save_company_dataset(self, data: dict) -> dict:
        with SessionLocal() as db:
            return self.company_service.save_company_dataset(db, data)

    def list_company_summaries(self) -> list[dict]:
        with SessionLocal() as db:
            return self.company_service.list_company_summaries(db)

    def bootstrap_from_local_files(self) -> dict:
        with SessionLocal() as db:
            return self.company_service.bootstrap_from_local_files(db)

    def backfill_structured_tables_from_local_files(self) -> dict:
        with SessionLocal() as db:
            return self.company_service.backfill_structured_tables_from_local_files(db)

    def to_compact_dataset(self, data: dict) -> dict:
        return self.local_store.to_compact_dataset(data)
