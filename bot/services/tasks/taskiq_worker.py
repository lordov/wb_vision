import asyncio
from taskiq import TaskiqEvents, TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from bot.core.dependency.container_init import init_container
from taskiq_nats import NatsBroker, PushBasedJetStreamBroker
from bot.core.config import settings

broker = PushBasedJetStreamBroker(
    settings.nats.url,
    queue="wb_tasks",
)
scheduler = TaskiqScheduler(broker, sources=[LabelScheduleSource(broker)])


@broker.task(schedule=[{'cron': '*/5 * * * *'}])
async def test_task():
    print("test_task")


async def main():
    # 1) Инициализация контейнера (тот же container_init!)
    container = init_container()

    # 3) Стартуем воркер
    await broker.startup()

if __name__ == "__main__":
    asyncio.run(main())