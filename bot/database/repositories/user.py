from ..models import User
from .base import SQLAlchemyRepository


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from bot.core.logging import db_logger


class UserRepository(SQLAlchemyRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        try:
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            db_logger.info("user.lookup", telegram_id=telegram_id,
                        found=bool(user))
            return user
        except SQLAlchemyError as e:
            db_logger.error("user.lookup.failed",
                         telegram_id=telegram_id, error=str(e))
            raise

    async def get_or_create(
        self, telegram_id: int, username: str, locale: str = "ru"
    ) -> User:
        try:
            user = await self.get_by_telegram_id(telegram_id)
            if user:
                if user.is_blocked:
                    user.is_blocked = False
                db_logger.info("user.exists", telegram_id=telegram_id)
                return user

            user = await self.add_one({
                "telegram_id": telegram_id,
                "username": username,
                "locale": locale,
            })
            db_logger.info("user.created", telegram_id=telegram_id,
                        username=username)
            return user
        except SQLAlchemyError as e:
            db_logger.error("user.create.failed",
                         telegram_id=telegram_id, error=str(e))
            raise
