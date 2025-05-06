from cryptography.fernet import Fernet
from fluentogram import TranslatorHub
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.core.config import settings
from bot.core.dependency.container import DependencyContainer
from bot.utils.i18n import create_translator_hub


# Опционально кэшируем, чтобы не пересоздавался при каждом вызове в рамках одного процесса
_container: DependencyContainer | None = None


def init_container(reuse: bool = True) -> DependencyContainer:
    global _container
    if _container is not None and reuse:
        return _container

    # 1. Создание движка и session_maker
    engine = create_async_engine(
        settings.postgres.async_url,
        echo=settings.debug,
        pool_size=5,
        max_overflow=10,
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    # 2. Шифрование
    fernet = Fernet(settings.fernet_secret.get_secret_value())

    # 3. Локализация
    translator_hub: TranslatorHub = create_translator_hub()

    # 4. Сборка контейнера
    _container = DependencyContainer(
        bot_token=settings.bot.token.get_secret_value(),
        i18n=translator_hub,
        fernet=fernet,
        session_maker=session_maker,
    )
    return _container
