import asyncio
import taskiq_aiogram
from aiogram.exceptions import TelegramForbiddenError

from typing import Annotated
from taskiq import Context, TaskiqDepends, TaskiqEvents, TaskiqScheduler, TaskiqState
from taskiq.schedule_sources import LabelScheduleSource
from taskiq.middlewares.prometheus_middleware import PrometheusMiddleware
from taskiq_nats import PullBasedJetStreamBroker, NATSObjectStoreResultBackend
from nats.js.api import ConsumerConfig

from bot.core.config import settings
from bot.core.dependency.container import DependencyContainer
from bot.core.dependency.container_init import init_container
from bot.services.task_control import TaskName
from bot.api.base_api_client import UnauthorizedUser
from bot.core.logging import app_logger


# Разделение стримов для ручных задач и задач, запускаемых по расписанию
broker = PullBasedJetStreamBroker(
    settings.nats.url,
    stream_name="taskiq_jetstream",
    durable="wb_tasks",
    consumer_config=ConsumerConfig(
        ack_wait=60 * 5,  # Уменьшаем время ожидания до 5 минут
        max_deliver=2,
        max_ack_pending=3
    ),
).with_result_backend(NATSObjectStoreResultBackend(settings.nats.url))

broker.add_middlewares(
    PrometheusMiddleware(
        server_addr="0.0.0.0",
        server_port=9000,
        # Путь для хранения метрик в многопроцессной среде
        metrics_path=None  # Использует временную директорию по умолчанию
    ),
)

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
    state.container = container

    # КРИТИЧЕСКИ ВАЖНО: восстанавливаем состояние после перезапуска контейнеров
    async with await container.create_uow() as uow:
        task_control = container.get_task_control_service(uow)

        # Помечаем ВСЕ задачи в статусе 'running' как failed
        # так как после перезапуска контейнеров мы не можем знать их реальное состояние
        recovered_count = await task_control.recover_all_running_tasks()

        app_logger.info(
            f"Container restart: recovered {recovered_count} running tasks")


def container_dep(context: Annotated[Context, TaskiqDepends()]) -> DependencyContainer:
    return context.state.container


@broker.task()
async def load_info(
    telegram_id: int,
    container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]
):
    # Первая транзакция: получаем данные и регистрируем начало задачи
    async with await container.create_uow() as uow:
        api_service = container.get_api_key_service(uow)
        task_control = container.get_task_control_service(uow)

        try:
            api_key = await api_service.get_user_key(telegram_id=telegram_id)
            user_id = api_key.user_id

            # Проверяем и регистрируем задачу
            if not await task_control.start_task(user_id, TaskName.PRE_LOAD_INFO):
                app_logger.info(f'Pre-load orders task blocked for user {user_id}')
                return
            
            # Транзакция автоматически коммитится при выходе из контекста
            app_logger.info(f'Task PRE_LOAD_INFO started for user {user_id}')
            
        except Exception as e:
            app_logger.error(f'Failed to start PRE_LOAD_INFO task for telegram_id {telegram_id}: {e}')
            return

    # Вторая транзакция: выполняем основную работу
    try:
        async with await container.create_uow() as uow:
            wb_service = container.get_wb_service(uow)
            
            app_logger.info(f'Pre-loaded info for {telegram_id}')
            await wb_service.pre_load_orders(user_id, api_key.key_encrypted)
            await wb_service.load_stocks(user_id, api_key.key_encrypted)

    except UnauthorizedUser as e:
        # Третья транзакция: завершаем задачу с ошибкой
        async with await container.create_uow() as uow:
            task_control = container.get_task_control_service(uow)
            await task_control.complete_task(
                user_id, TaskName.PRE_LOAD_INFO, success=False,
                error_message=f"{e.message}")
        return

    except Exception as e:
        app_logger.error(f'PRE_LOAD_INFO failed for telegram_id {telegram_id}: {e}')
        # Третья транзакция: завершаем задачу с ошибкой
        async with await container.create_uow() as uow:
            task_control = container.get_task_control_service(uow)
            await task_control.complete_task(
                user_id, TaskName.PRE_LOAD_INFO, success=False, error_message=str(e))
        raise

    # Третья транзакция: завершаем задачу успешно
    async with await container.create_uow() as uow:
        task_control = container.get_task_control_service(uow)
        await task_control.complete_task(user_id, TaskName.PRE_LOAD_INFO, success=True)


@broker.task(schedule=[{"cron": "*/30 * * * *"}])
async def cron_load_stocks(
    container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]
):
    async with await container.create_uow() as uow:
        api_service = container.get_api_key_service(uow)
        task_control = container.get_task_control_service(uow)

        api_keys = await api_service.get_all_decrypted_keys()
        api_user_ids = [key.user_id for key in api_keys]
        available_user_ids = await task_control.get_available_users_for_task(
            api_user_ids,
            TaskName.LOAD_STOCKS
        )
        # Фильтруем ключи по доступным пользователям
        available_keys = [
            key for key in api_keys if key.user_id in available_user_ids]

        for key in available_keys:
            if await task_control.start_task(key.user_id, TaskName.LOAD_STOCKS):
                await load_stocks(key.user_id, key.key_encrypted)
            else:
                app_logger.info(f'LOAD_STOCKS blocked for user {key.user_id}')

        app_logger.info(f'Loaded stocks for {len(api_keys)} users')


@broker.task
async def load_stocks(
    user_id: int,
    api_key: str,
    container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]
):
    async with await container.create_uow() as uow:
        wb_service = container.get_wb_service(uow)
        task_control = container.get_task_control_service(uow)

        try:
            await wb_service.load_stocks(user_id, api_key)
            await task_control.complete_task(user_id, TaskName.LOAD_STOCKS, success=True)

        except UnauthorizedUser as e:
            await task_control.complete_task(
                user_id, TaskName.LOAD_STOCKS, success=False,
                error_message=f"{e.message}")
            return
        except Exception as e:
            app_logger.error(f'Load stocks failed for user {user_id}: {e}')
            await task_control.complete_task(
                user_id, TaskName.LOAD_STOCKS, success=False, error_message=str(e))
            raise


@broker.task(schedule=[{"cron": "*/10 * * * *"}])
async def start_orders_notif(
    container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]
) -> None:
    async with await container.create_uow() as uow:
        api_service = container.get_api_key_service(uow)
        task_control = container.get_task_control_service(uow)

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
    try:
        async with await container.create_uow() as uow:
            service = container.get_wb_service(uow)
            task_control = container.get_task_control_service(uow)
            try:
                texts = await service.fetch_and_save_orders(api_key=api_key, user_id=user_id)
            except UnauthorizedUser as e:
                await task_control.complete_task(
                    user_id, TaskName.START_NOTIF_PIPELINE, success=False,
                    error_message=f"{e.message}")
                return

        if not texts:
            app_logger.info(
                f'No new orders for user {user_id}, completing pipeline')
            # Завершаем пайплайн, так как нет новых заказов
            await task_control.complete_task(user_id, TaskName.START_NOTIF_PIPELINE, success=True)
            return

        if texts:
            await notify_user_about_orders.kiq(telegram_id, texts, user_id)

    except Exception as e:
        app_logger.error(
            f'Fetch and save orders failed for user {user_id}: {e}')
        await task_control.complete_task(
            user_id, TaskName.START_NOTIF_PIPELINE, success=False, error_message=str(e))
        raise


@broker.task()
async def notify_user_about_orders(
    telegram_id: int,
    texts: list[dict],
    user_id: int,
    container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]
):
    async with await container.create_uow() as uow:
        notify = container.get_notification_service(uow)
        task_control = container.get_task_control_service(uow)
        employee_service = container.get_user_service(uow)
        employees = await employee_service.get_active_employees(telegram_id)
        all_telegram_ids = [employee.telegram_id for employee in employees]

        for telegram_id in all_telegram_ids:
            await notify_employee.kiq(telegram_id, texts)

        try:
            await notify.send_message(telegram_id, texts)
            # Завершаем пайплайн после успешной отправки всех сообщений
            await task_control.complete_task(user_id, TaskName.START_NOTIF_PIPELINE, success=True)
            app_logger.info(
                f'Pipeline completed successfully for user {user_id}')

        except TelegramForbiddenError as e:
            await task_control.complete_task(
                user_id, TaskName.START_NOTIF_PIPELINE, success=False, error_message=f"{e.message}")
            return

        except Exception as e:
            app_logger.error(f'Notification failed for user {user_id}: {e}')
            await task_control.complete_task(
                user_id, TaskName.START_NOTIF_PIPELINE, success=False, error_message=str(e))
            raise


@broker.task()
async def notify_employee(
    telegram_id: int,
    texts: list[dict],
    container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]
):
    async with await container.create_uow() as uow:
        notify = container.get_notification_service(uow)
        try:
            await notify.send_message(telegram_id, texts)
            app_logger.info(
                f'Notification sent to employee {telegram_id}')
        except TelegramForbiddenError as e:
            app_logger.warning(
                f"Cannot send message to {telegram_id}: user blocked the bot")
            return
        except Exception as e:
            app_logger.error(
                f"Failed to send message to {telegram_id}: {e}")


@broker.task(schedule=[{"cron": "0 2 * * *"}])  # Каждый день в 2:00
async def cleanup_old_tasks(
    container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]
) -> None:
    """Очистка старых завершенных задач."""
    async with await container.create_uow() as uow:
        task_control = container.get_task_control_service(uow)
        cleaned_count = await task_control.cleanup_old_tasks(days_old=7)
        app_logger.info(f'Cleaned up {cleaned_count} old task records')


async def main() -> None:
    try:
        await broker.startup()
        await start_orders_notif()
        await broker.shutdown()
    except (Exception, TimeoutError) as e:
        print(e)
        await broker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
