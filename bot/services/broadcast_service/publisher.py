import json

from sqlalchemy.ext.asyncio import AsyncSession
from nats.js.client import JetStreamContext
from datetime import datetime

from bot.database.orm_query import get_all_users
from bot.database.models import User


async def publish_broadcast_message(
    js: JetStreamContext,
    session: AsyncSession,
    message_data: dict,
    subject: str,
    delay: int = 0
):

    # Получаем список пользователей из базы данных
    users: list[User] = await get_all_users(session)
    for user in users:
        headers = {
            'Tg-Broadcast-Chat-ID': str(user.user_id),
            'Tg-Broadcast-Msg-Timestamp': str(datetime.now().timestamp()),
            'Tg-Broadcast-Msg-Delay': str(delay),
        }
        # В message_data можем хранить текст, фото и URL
        payload = json.dumps(message_data).encode('utf-8')
        await js.publish(subject=subject, payload=payload, headers=headers)
