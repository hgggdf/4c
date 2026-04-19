from sqlalchemy.orm import Session

from database.base import Base
from database.session import engine
from repository.user_repo import UserRepository
from repository.watchlist_repo import WatchlistRepository
import models  # noqa: F401


def init_database() -> None:
    Base.metadata.create_all(bind=engine)

    user_repo = UserRepository()
    watchlist_repo = WatchlistRepository()

    with Session(engine) as db:
        user = user_repo.get_or_create_demo_user(db)
        if not watchlist_repo.list_by_user(db, user.id):
            watchlist_repo.seed_default(db, user.id)
