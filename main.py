import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram.fsm.storage.memory import MemoryStorage

from aiogram_dialog import setup_dialogs
from fluentogram import TranslatorHub

from redis.asyncio.client import Redis
from redis.exceptions import ConnectionError

from bot.core.config import settings
from bot.core.dependency.container_init import init_container
from bot.core.dependency.container import DependencyContainer
# from tgbot.dialogs.admin_dialog import admin_panel
from bot.core.logging import setup_logging, app_logger
from bot.handlers.dialogs.user.main_menu.dialog import user_panel
from bot.handlers.dialogs.user.api_connect.dialog import api_connect
from bot.handlers.dialogs.user.employee.dialog import employee
# from tgbot.dialogs.broadcast_dialog import broadcast_dialog

from bot.database.engine import async_session_maker, engine
from bot.middlewares.uow import UnitOfWorkMiddleware
from bot.middlewares.i18n import TranslatorRunnerMiddleware
from bot.utils.logger_config import configure_logging
from bot.utils.i18n import create_translator_hub
from bot.utils.nats_connect import connect_to_nats
from bot.utils.start_consumer import start_broadcast_consumer
from bot.handlers import get_routers


async def setup_dispatcher(container: DependencyContainer) -> Dispatcher:
    """
    Function to set up the dispatcher (Dispatcher).

    Tries to establish a connection with Redis and creates a data storage
    (RedisStorage) or, if the connection with Redis fails, uses a data storage
    in memory (MemoryStorage).

    Returns:
        Dispatcher: The aiogram dispatcher object.
    """

    # Create a Redis client
    redis = Redis()

    try:
        # Try to ping Redis
        await redis.ping()

        # If successful, create a Redis storage
        storage = RedisStorage(
            redis=redis, key_builder=DefaultKeyBuilder(with_destiny=True))
        print("Используется Redis.")
    except ConnectionError:
        # If Redis is not available, use a memory storage instead
        print("Redis is not available, using MemoryStorage instead.")
        storage = MemoryStorage()

    # Create a dispatcher with the chosen storage
    dp = Dispatcher(db_engine=engine, storage=storage, container=container)
    dp.update.outer_middleware(UnitOfWorkMiddleware(
        session_pool=async_session_maker))
    dp.update.middleware(TranslatorRunnerMiddleware())

    return dp


async def setup_bot(dp: Dispatcher) -> Bot:
    """
    Function to set up the bot (Bot).
    Here we also register routers and dialogs.

    Args:
        dp (Dispatcher): The aiogram dispatcher object.

    Returns:
        Bot: The aiogram bot object.
    """
    bot: Bot = Bot(
        token=settings.bot.token.get_secret_value(),
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    dp.include_routers(*get_routers())
    dp.include_routers(user_panel, api_connect, employee)

    setup_dialogs(dp)

    return bot


async def main():
    setup_logging()
    app_logger.info('Starting bot...', context='init')
    translator_hub: TranslatorHub = create_translator_hub()

    container = init_container()

    # Set up the dispatcher with the chosen storage
    dp: Dispatcher = await setup_dispatcher(container)

    # Set up the bot with the provided token and default properties
    bot: Bot = await setup_bot(dp)

    try:
        await bot.send_message(settings.bot.admin_id, f'Бот запущен.')
    except Exception as e:
        print(e)

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await asyncio.gather(
            dp.start_polling(
                bot,
                _translator_hub=translator_hub
            ),
        )
    except Exception as e:
        app_logger.error(e)
    finally:
        # await nc.close()
        app_logger.info('Connection to NATS closed')


# Запуск бота
if __name__ == '__main__':
    configure_logging()
    asyncio.run(main())
