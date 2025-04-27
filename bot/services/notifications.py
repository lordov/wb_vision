from aiogram import Bot
from bot.core.logging import app_logger


class NotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = app_logger

    async def send_message(self, user_id: int, text: str) -> None:
        """Отправка сообщения одному пользователю."""
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            self.logger.info("Message sent", user_id=user_id)
        except Exception as e:
            self.logger.error("Failed to send message",
                              user_id=user_id, error=str(e))

    async def send_many_messages(self, user_ids: list[int], text: str) -> None:
        """Массовая отправка сообщений."""
        for user_id in user_ids:
            await self.send_message(user_id, text)
