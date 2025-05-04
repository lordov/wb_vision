# bot/core/dependency/container_init.py
from cryptography.fernet import Fernet
from fluentogram import TranslatorHub
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.core.config import settings
from bot.core.dependency.container import DependencyContainer
from bot.utils.i18n import create_translator_hub

def init_container() -> DependencyContainer:
    # 1) Создаём engine и session_maker
    engine = create_async_engine(settings.postgres.async_url, echo=True)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    # 2) Настраиваем i18n и шифрование
    fernet = Fernet(settings.fernet_secret.get_secret_value())
    translator_hub: TranslatorHub = create_translator_hub()
    # 3) Собираем контейнер
    return DependencyContainer(
        bot_token=settings.bot.token.get_secret_value(),
        i18n=translator_hub,
        fernet=fernet,
        session_maker=session_maker,
    )
