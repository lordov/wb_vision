import asyncio
import taskiq_aiogram
from aiogram import Bot

from typing import Annotated
from taskiq import Context, TaskiqDepends, TaskiqEvents, TaskiqScheduler, TaskiqState
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_nats import PullBasedJetStreamBroker, NATSObjectStoreResultBackend
from nats.js.api import ConsumerConfig

from bot.core.config import settings
from bot.core.dependency.container import DependencyContainer
from bot.core.dependency.container_init import init_container
from bot.services.api_key import ApiKeyService
from bot.services.notifications import NotificationService
from bot.services.wb_service import WBService
from bot.core.logging import app_logger


# Для прода
broker = PullBasedJetStreamBroker(
    settings.nats.url,
    stream_name="taskiq_jetstream",
    durable="wb_tasks",
    consumer_config=ConsumerConfig(
        # Сколько можем дожидаться ответа, уменьшить размер задач
        ack_wait=60 * 5
    ),

).with_result_backend(NATSObjectStoreResultBackend(settings.nats.url))
taskiq_aiogram.init(
    broker,
    "main:dp",
    "main:bot",
)
scheduler = TaskiqScheduler(
    broker,
    sources=[LabelScheduleSource(broker)]
)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup(state: TaskiqState) -> None:
    container = init_container()
    # Here we store connection pool on startup for later use.
    state.container = container


def container_dep(context: Annotated[Context, TaskiqDepends()]) -> DependencyContainer:
    return context.state.container


@broker.task(task_name="my_task")
async def my_task(chat_id: int, bot: Bot = TaskiqDepends()) -> None:
    print("I'm a task")
    await asyncio.sleep(4)
    await bot.send_message(chat_id, "task completed")


@broker.task
async def add_one(
    value: int,
    container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]
) -> int:
    print(f"Executing add_one with value={value}")
    bot = container.bot
    await bot.send_message(settings.bot.admin_id, f"Executing add_one with value={value}")
    await asyncio.sleep(1)
    return value * value


@broker.task
async def pre_load_orders(
    telegram_id: int,
    container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]
):
    app_logger.info(f'Pre-loaded orders for {telegram_id}')
    wb_service = await container.get(WBService)
    api_service = await container.get(ApiKeyService)
    api_key = await api_service.get_user_key(telegram_id=telegram_id)
    await wb_service.pre_load_orders(api_key.user_id, api_key.key_encrypted)


@broker.task(schedule=[{"cron": "*/10 * * * *"}])
async def start_notif_pipline(container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]) -> None:
    api_service = await container.get(ApiKeyService)
    api_keys = await api_service.get_all_decrypted_keys()
    for key in api_keys:
        await fetch_and_save_orders_for_key.kiq(
            user_id=key.user_id,
            api_key=key.key_encrypted,
            telegram_id=key.telegram_id,
        )
    app_logger.info(f'Задача о заказах отправлена', user_id=key.user_id)


@broker.task
async def fetch_and_save_orders_for_key(
    user_id: int,
    telegram_id: int,
    api_key: str,
    container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]
):
    service = await container.get(WBService)
    texts = await service.fetch_and_save_orders(api_key=api_key, user_id=user_id)
    if not texts:
        app_logger.info(f'Cancel task for {user_id}')
        return

    if texts:
        await notify_user_about_orders.kiq(telegram_id, texts)


@broker.task()
async def notify_user_about_orders(
    telegram_id: int,
    texts: list[dict],
    container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]
):
    service = await container.get(NotificationService)
    await service.send_message(telegram_id=telegram_id, texts=texts)
    app_logger.info(f'Start notification for {telegram_id}')


async def main() -> None:
    try:
        await broker.startup()
        await start_notif_pipline.kiq()
        await broker.shutdown()
    except (Exception, TimeoutError) as e:
        print(e)
        await broker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
