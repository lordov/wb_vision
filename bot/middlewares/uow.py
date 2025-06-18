from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from sqlalchemy.ext.asyncio import async_sessionmaker
from bot.core.logging import db_logger
from bot.database.uow import UnitOfWork


class UnitOfWorkMiddleware(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker):
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        async with self.session_pool() as session:
            uow = UnitOfWork(session)
            try:
                data["uow"] = uow
                result = await handler(event, data)
                await uow.commit()
                return result
            except Exception as e:
                await uow.rollback()
                db_logger.error(f"UnitOfWorkMiddleware: {e}")
                raise
            finally:
                await uow.close()
