import logging

from aiogram import Bot
from bot.services.broadcast_service.consumer import BroadcastMessageConsumer

from nats.aio.client import Client
from nats.js.client import JetStreamContext

logger = logging.getLogger(__name__)


async def start_broadcast_consumer(
        nc: Client,
        js: JetStreamContext,
        bot: Bot,
        subject: str,
        stream: str,
        durable_name: str,
        rate_limit: int = 29,
        # max_deliver: int = 5,
        # ack_wait: timedelta = timedelta(seconds=30)
) -> None:
    consumer = BroadcastMessageConsumer(
        nc=nc,
        js=js,
        bot=bot,
        subject=subject,
        stream=stream,
        durable_name=durable_name,
        rate_limit=rate_limit,
        # max_deliver=max_deliver,
        # ack_wait=ack_wait
    )
    logger.info('Start broadcast message consumer')
    await consumer.start()
