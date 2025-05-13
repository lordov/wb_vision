from typing import Annotated
from taskiq import Context, InMemoryBroker, TaskiqDepends, TaskiqEvents, TaskiqState
from taskiq_nats import PullBasedJetStreamBroker, NATSObjectStoreResultBackend

from bot.core.config import settings
import asyncio

from bot.core.dependency.container import DependencyContainer
from bot.core.dependency.container_init import init_container
from bot.database.models import ApiKey
from bot.services.api_key import ApiKeyService
from bot.services.notifications import NotificationService
from bot.services.wb_service import WBService


# Для прода
broker = PullBasedJetStreamBroker(
    settings.nats.url,
    stream_name="taskiq_jetstream",
    durable="wb_tasks",
).with_result_backend(NATSObjectStoreResultBackend(settings.nats.url))
# broker.add_middlewares(SimpleRetryMiddleware())
# scheduler = TaskiqScheduler(broker, sources=[LabelScheduleSource(broker)])

# для тестов
# broker = InMemoryBroker()


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup(state: TaskiqState) -> None:
    container = init_container()
    # Here we store connection pool on startup for later use.
    state.container = container


def container_dep(context: Annotated[Context, TaskiqDepends()]) -> DependencyContainer:
    return context.state.container


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
async def fetch_orders_for_all_keys(container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]) -> None:
    service = await container.get(ApiKeyService)
    async with await container.create_uow():
        api_keys = await service.get_all_decrypted_keys()
        for key in api_keys:
            await fetch_and_save_orders_for_key.kiq(
            user_id=key.user_id,
            key_encrypted=key.key_encrypted,
        )
        print(f'{key.key_encrypted} отправлен в задачу')


@broker.task
async def fetch_and_save_orders_for_key(
    user_id: int,
    key_encrypted: str,
    container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]
) -> None:
    async with await container.create_uow():
        service = await container.get(WBService)
        new_orders = await service.fetch_and_save_orders(api_key=key_encrypted, user_id=user_id)

        if new_orders:
            await notify_user_about_orders.kiq(user_id, new_orders)


@broker.task
async def notify_user_about_orders(
    user_id: int, orders: list[dict],
    container: Annotated[DependencyContainer, TaskiqDepends(container_dep)]
) -> None:
    # Здесь можно форматировать сообщение под пользователя
    service = await container.get(NotificationService)
    await service.send_message(user_id=user_id, orders=orders)


async def main() -> None:
    try:
        await broker.startup()
        task = await fetch_orders_for_all_keys.kiq()
        api_keys = await task.wait_result(timeout=6000)
        await broker.shutdown()
    except (Exception, TimeoutError) as e:
        print(e)
        await broker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
