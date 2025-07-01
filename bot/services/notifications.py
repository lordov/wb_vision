from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from fluentogram import TranslatorHub
from bot.database.uow import UnitOfWork
from bot.core.logging import app_logger
from aiolimiter import AsyncLimiter

# 1 запрос в секунду на пользователя
user_limiters: dict[int, AsyncLimiter] = {}


def get_user_limiter(user_id: int) -> AsyncLimiter:
    if user_id not in user_limiters:
        # 1 message per 5 second
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
            texts: list[dict],
    ) -> None:
        limiter = get_user_limiter(telegram_id)
        for text in texts:
            try:
                app_logger.info("Sending notification", user_id=telegram_id)
                async with limiter:
                    await self.bot.send_photo(
                        chat_id=telegram_id,
                        photo=text.get('photo'),
                        caption=text.get('text'), parse_mode="HTML"
                    )
            except TelegramForbiddenError as e:
                await self.uow.users.block_user(telegram_id)
                raise e
            except Exception as e:
                print(e)

    async def notify_api_key_deactivated(self, telegram_id: int) -> None:
        """
        Отправляет уведомление пользователю о деактивации API ключа.

        Args:
            telegram_id: Telegram ID пользователя
        """
        try:
            app_logger.info(
                f"Sending API key deactivation message to {telegram_id}")

            limiter = get_user_limiter(telegram_id)
            async with limiter:
                await self.bot.send_message(
                    chat_id=telegram_id,
                    text=self.i18n.get('api-key-deactivated'),
                    parse_mode="HTML"
                )

            app_logger.info(
                f"API key deactivation message sent to {telegram_id}")

        except TelegramForbiddenError:
            await self.uow.users.block_user(telegram_id)
            app_logger.warning(
                f"Cannot send message to {telegram_id}: user blocked the bot")
        except Exception as e:
            app_logger.error(
                f"Failed to send API key deactivation message to {telegram_id}: {e}")
            raise
