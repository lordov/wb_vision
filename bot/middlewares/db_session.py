import asyncio
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from bot.utils.logger_config import logging


db_logger = logging.getLogger('db_logger')


class DataBaseSession(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker):
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        retries = 5  # Количество попыток повтора операции
        for attempt in range(retries):
            try:
                async with self.session_pool() as session:
                    data['session'] = session
                    return await handler(event, data)
            except OperationalError as exc:
                db_logger.warning(
                    f"OperationalError occurred: {exc}. Retrying ({attempt + 1}/{retries})..."
                )
                # Подождать немного перед следующей попыткой
                await asyncio.sleep(2)
            except SQLAlchemyError as e:
                db_logger.error(f'Ошибка SqlAlchemy: {e}')

        db_logger.error(f"Failed after {retries} retries.")
        return None  # Или возбудить исключение, если нужно
