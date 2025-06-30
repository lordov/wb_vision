from ..models import User
from .base import SQLAlchemyRepository


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from bot.core.logging import db_logger


class UserRepository(SQLAlchemyRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_tg_id(self, telegram_id: int) -> User | None:
        try:
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            db_logger.info("user.lookup.by.telegram_id", telegram_id=telegram_id,
                           found=bool(user))
            return user
        except SQLAlchemyError as e:
            db_logger.error("user.lookup.failed.by.telegram_id",
                            telegram_id=telegram_id, error=str(e))
            raise

    async def add_user(
        self, telegram_id: int, username: str, locale: str = "ru"
    ) -> User:
        try:
            user = await self.get_by_tg_id(telegram_id)
            if user:
                if not user.is_active:
                    user.is_active = True
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

    async def get_by_user_id(self, user_id: int) -> User | None:
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            db_logger.info("user.lookup.by.id", id=user_id,
                           found=bool(user))
            return user
        except SQLAlchemyError as e:
            db_logger.error("user.lookup.failed.by.id",
                            id=user_id, error=str(e))
            raise

    async def block_user(self, telegram_id: int) -> None:
        try:
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            user.is_active = False
            db_logger.info("user.blocked", telegram_id=telegram_id)

        except SQLAlchemyError as e:
            db_logger.error("user.block.failed",
                            telegram_id=telegram_id, error=str(e))
            raise
