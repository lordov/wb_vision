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
from bot.services.task_control import TaskControlService, TaskName
from bot.core.logging import app_logger


# Для прода
broker = PullBasedJetStreamBroker(
    settings.nats.url,
    stream_name="taskiq_jetstream",
    durable="wb_tasks",
    consumer_config=ConsumerConfig(
        # Сколько можем дожидаться ответа, уменьшить размер задач
        ack_wait=60 * 3,
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
    wb_service = await container.get(WBService)
    api_service = await container.get(ApiKeyService)
    task_control = await container.get(TaskControlService)

    api_key = await api_service.get_user_key(telegram_id=telegram_id)
    user_id = api_key.user_id

    # Проверяем и регистрируем задачу
    if not await task_control.start_task(user_id, TaskName.PRE_LOAD_ORDERS):
        app_logger.info(f'Pre-load orders task blocked for user {user_id}')
        return

    try:
        app_logger.info(f'Pre-loaded orders for {telegram_id}')
        await wb_service.pre_load_orders(user_id, api_key.key_encrypted)

        # Отмечаем задачу как завершенную
        await task_control.complete_task(user_id, TaskName.PRE_LOAD_ORDERS, success=True)

    except Exception as e:
        # Отмечаем задачу как неудачную
        await task_control.complete_task(
            user_id,
            TaskName.PRE_LOAD_ORDERS,
            success=False,
            error_message=str(e)
        )
        app_logger.error(f'Pre-load orders failed for {user_id}: {e}')
        raise


@broker.task(schedule=[{"cron": "*/10 * * * *"}])
async def start_notif_pipline(container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]) -> None:
    api_service = await container.get(ApiKeyService)
    task_control = await container.get(TaskControlService)

    # Получаем все ключи
    api_keys = await api_service.get_all_decrypted_keys()
    all_user_ids = [key.user_id for key in api_keys]

    # Получаем пользователей, для которых можно запустить пайплайн уведомлений
    available_user_ids = await task_control.get_available_users_for_task(
        all_user_ids,
        TaskName.START_NOTIF_PIPELINE
    )

    # Фильтруем ключи по доступным пользователям
    available_keys = [
        key for key in api_keys if key.user_id in available_user_ids]

    # Запускаем пайплайн для каждого доступного пользователя
    started_pipelines = 0
    for key in available_keys:
        # Регистрируем начало пайплайна для пользователя
        if await task_control.start_task(key.user_id, TaskName.START_NOTIF_PIPELINE):
            await fetch_and_save_orders_for_key.kiq(
                user_id=key.user_id,
                api_key=key.key_encrypted,
                telegram_id=key.telegram_id,
            )
            started_pipelines += 1
        else:
            app_logger.info(
                f'START_NOTIF_PIPELINE blocked for user {key.user_id}')

    app_logger.info(
        f'Пайплайны уведомлений запущены для {started_pipelines}/{len(api_keys)} пользователей',
        started_count=started_pipelines,
        total_count=len(api_keys)
    )


@broker.task
async def fetch_and_save_orders_for_key(
    user_id: int,
    telegram_id: int,
    api_key: str,
    container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]
):
    service = await container.get(WBService)
    task_control = await container.get(TaskControlService)

    texts = await service.fetch_and_save_orders(api_key=api_key, user_id=user_id)

    if not texts:
        app_logger.info(
            f'No new orders for user {user_id}, completing pipeline')
        # Завершаем пайплайн, так как нет новых заказов
        await task_control.complete_task(user_id, TaskName.START_NOTIF_PIPELINE, success=True)
        return

    if texts:
        # Отправляем уведомления и передаем user_id для завершения пайплайна
        await notify_user_about_orders.kiq(telegram_id, texts, user_id)


@broker.task()
async def notify_user_about_orders(
    telegram_id: int,
    texts: list[dict],
    user_id: int,
    container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]
):
    service = await container.get(NotificationService)
    task_control = await container.get(TaskControlService)

    try:
        await service.send_message(telegram_id=telegram_id, texts=texts)
        app_logger.info(
            f'Notifications sent for telegram_id {telegram_id}, user_id {user_id}')

        # Завершаем пайплайн после успешной отправки всех сообщений
        await task_control.complete_task(user_id, TaskName.START_NOTIF_PIPELINE, success=True)
        app_logger.info(f'Pipeline completed successfully for user {user_id}')

    except Exception as e:
        app_logger.error(f'Notification failed for user {user_id}: {e}')


@broker.task(schedule=[{"cron": "0 2 * * *"}])  # Каждый день в 2:00
async def cleanup_old_tasks(container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]) -> None:
    """Очистка старых завершенных задач."""
    task_control = await container.get(TaskControlService)
    cleaned_count = await task_control.cleanup_old_tasks(days_old=7)
    app_logger.info(f'Cleaned up {cleaned_count} old task records')


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
