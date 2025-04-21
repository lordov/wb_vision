import logging
import json
import time

from aiolimiter import AsyncLimiter
from contextlib import suppress
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from nats.aio.client import Client
from nats.aio.msg import Msg
from nats.js import JetStreamContext
from nats.js.api import ConsumerConfig

from bot.database.engine import async_session_maker


error_logger = logging.getLogger('app_error_logger')
info_logger = logging.getLogger('app_info_logger')


class BroadcastMessageConsumer:
    def __init__(
            self,
            nc: Client,
            js: JetStreamContext,
            bot: Bot,
            subject: str,
            stream: str,
            durable_name: str,
            rate_limit: int = 29

    ) -> None:
        self.nc = nc
        self.js = js
        self.bot = bot
        self.subject = subject
        self.stream = stream
        self.durable_name = durable_name
        self.rate_limit = rate_limit
        self.limiter = AsyncLimiter(max_rate=rate_limit, time_period=1)

    async def start(self) -> None:
        self.stream_sub = await self.js.subscribe(
            subject=self.subject,
            stream=self.stream,
            cb=self.on_message,
            durable=self.durable_name,
            manual_ack=True,
            config=ConsumerConfig(
                max_deliver=1,
                ack_wait=300
            )
        )

    async def on_message(self, msg: Msg):
        start_time = time.time()
        async with self.limiter:
            try:
                chat_id = int(msg.headers.get('Tg-Broadcast-Chat-ID'))
                message_data = json.loads(msg.data.decode('utf-8'))
                await send_broadcast_message(self.bot, chat_id, message_data)
                elapsed_time = time.time() - start_time
                ack_info = await msg.ack()
                info_logger.info(
                    f"Message sent for chat_id {chat_id} "
                    f"in {elapsed_time:.2f} seconds"
                )
            except Exception as e:
                error_logger.error(f"Error sending message to {chat_id}: {e}")
                await msg.nak(delay=5)


async def send_broadcast_message(
        bot: Bot,
        chat_id: int,
        message_data: dict
):
    text = message_data.get('text')
    photo = message_data.get('photo')
    url = message_data.get('url')

    if url:
        button = InlineKeyboardButton(
            text="Перейти", callback_data="broadcast_click", url=url)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
    else:
        keyboard = None
    try:
        if photo:
            with suppress(TelegramBadRequest):

                await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )

        else:
            with suppress(TelegramBadRequest):
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=keyboard
                )
    except TelegramForbiddenError:
        async with async_session_maker() as session:
            ...
            # await mark_user_blocked(session, chat_id)
