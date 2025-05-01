import json
from aiogram import Bot
from bot.core.logging import app_logger
from nats.js.client import JetStreamContext


class NotificationService:
    def __init__(self, js: JetStreamContext, subject: str):
        self.js = js
        self.subject = subject

    async def send_message(self, user_id: int, text: str) -> None:
        headers = {
            "Tg-Broadcast-Chat-ID": str(user_id),
        }
        payload = json.dumps({"text": text}).encode("utf-8")
        await self.js.publish(
            subject=self.subject,
            payload=payload,
            headers=headers
        )
        app_logger.info(f"Message sent to {user_id}")
