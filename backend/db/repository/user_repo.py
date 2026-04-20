"""用户仓储。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import get_settings
from db.models.user import User

settings = get_settings()


class UserRepository:
    """负责系统用户的查询与默认演示用户初始化。"""

    def get_by_id(self, db: Session, user_id: int) -> User | None:
        """按主键查询用户。"""
        return db.get(User, user_id)

    def get_or_create_demo_user(self, db: Session) -> User:
        """获取默认演示用户；不存在时自动创建。"""
        user = self.get_by_id(db, settings.demo_user_id)
        if user:
            return user

        existing = db.scalar(select(User).where(User.username == settings.demo_username))
        if existing:
            return existing

        user = User(
            id=settings.demo_user_id,
            username=settings.demo_username,
            password_hash="demo_password_hash",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
