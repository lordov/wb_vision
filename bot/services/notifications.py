import asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from fluentogram import TranslatorRunner, TranslatorHub
from bot.database.uow import UnitOfWork
from bot.schemas.wb import OrderWBCreate
from bot.core.logging import app_logger
from aiolimiter import AsyncLimiter

# 1 запрос в секунду на пользователя
user_limiters: dict[int, AsyncLimiter] = {}


def get_user_limiter(user_id: int) -> AsyncLimiter:
    if user_id not in user_limiters:
        # 1 message per second
        user_limiters[user_id] = AsyncLimiter(1, 5)
    return user_limiters[user_id]


class NotificationService:
    def __init__(
            self,
            uow: UnitOfWork,
            i18n: TranslatorHub,
            bot: Bot
    ):
        self.uow = uow
        self.bot = bot
        self.i18n = i18n.get_translator_by_locale('ru')

    async def send_message(
            self,
            telegram_id: int,
            texts: list[str],
    ) -> None:
        limiter = get_user_limiter(telegram_id)
        for text in texts:
            try:
                app_logger.info("Sending notification", user_id=telegram_id)
                async with limiter:
                    await self.bot.send_photo(
                        chat_id=telegram_id,
                        photo=f"https://basket-12.wbbasket.ru/vol1711/part171150/171150581/images/c516x688/1.webp",
                        caption=text, parse_mode="HTML"
                    )
            except TelegramForbiddenError:
                ...
            except Exception as e:
                print(e)

    async def _get_photo(self, nm_id: int):
        "Находим фотку на вб"
        url = f"https://basket-12.wbbasket.ru/vol1711/part171150/171150581/images/c516x688/1.webp"
        return url
