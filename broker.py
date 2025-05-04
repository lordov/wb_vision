from typing import Annotated
from taskiq import Context, InMemoryBroker, TaskiqDepends, TaskiqEvents, TaskiqState
from taskiq_nats import PullBasedJetStreamBroker, NATSObjectStoreResultBackend

from bot.core.config import settings
import asyncio

from bot.core.dependency.container import DependencyContainer
from bot.core.dependency.container_init import init_container


# Для прода
# broker = PullBasedJetStreamBroker(
#     settings.nats.url,
#     stream_name="taskiq_jetstream",
#     durable="wb_tasks",
# ).with_result_backend(NATSObjectStoreResultBackend(settings.nats.url))

# для тестов
broker = InMemoryBroker()
# broker.add_middlewares(SimpleRetryMiddleware())
# scheduler = TaskiqScheduler(broker, sources=[LabelScheduleSource(broker)])

@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup(state: TaskiqState) -> None:
    container = init_container()
    # Here we store connection pool on startup for later use.
    state.container = container

@broker.task
async def add_one(value: int, context: Annotated[Context, TaskiqDepends()]) -> int:
    print(f"Executing add_one with value={value}")
    container: DependencyContainer =context.state.container
    bot = container.bot
    await asyncio.sleep(1)
    return value * value


async def main() -> None:
    # Never forget to call startup in the beginning.
    await broker.startup()
    # Send the task to the broker.
    task = await add_one.kiq(15)
    # Wait for the result.
    result = await task.wait_result(timeout=30)
    print(f"Task execution took: {result.execution_time} seconds.")
    if not result.is_err:
        print(f"Returned value: {result.return_value}")
    else:
        print("Error found while executing task.")
    await broker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
