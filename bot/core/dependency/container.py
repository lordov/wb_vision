from typing import Callable
from aiogram import Bot
from cryptography.fernet import Fernet
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from taskiq_nats import NatsBroker
from bot.services.tasks.taskiq_worker import broker

from bot.services.notifications import NotificationService
from bot.services.api_key import ApiKeyService
from bot.services.subscription import SubscriptionService
from bot.services.wb_service import WBService
from bot.database.uow import UnitOfWork


class DependencyContainer:
    def __init__(
        self,
        bot_token: str,
        i18n: TranslatorRunner,
        fernet: Fernet,
        session_maker: Callable[[], AsyncSession]
    ) -> None:
        # Приватные аттрибуты
        self._bot_token = bot_token
        self._fernet = fernet
        self._session_maker = session_maker
        self._i18n = i18n

        # Ленивая инициализация сервисов
        self._bot = None
        self._notification_service = None
        self._api_key_service = None
        self._subscription_service = None
        self._wb_service = None
        self._broker = None

    @property
    def bot(self) -> Bot:
        if self._bot is None:
            self._bot = Bot(token=self._bot_token)  # Используем _bot_token
        return self._bot

    async def create_uow(self) -> UnitOfWork:
        """Создает новый UnitOfWork с новой сессией."""
        session = self._session_maker()  # Используем _session_maker
        uow = UnitOfWork(session)
        return uow

    @property
    async def notification_service(self) -> NotificationService:
        if self._notification_service is None:
            self._notification_service = NotificationService(bot=self.bot)
        return self._notification_service

    @property
    async def api_key_service(self) -> ApiKeyService:
        if self._api_key_service is None:
            uow = await self.create_uow()  # Создаем UnitOfWork
            self._api_key_service = ApiKeyService(uow=uow, fernet=self._fernet)
        return self._api_key_service

    @property
    async def subscription_service(self) -> SubscriptionService:
        if self._subscription_service is None:
            uow = await self.create_uow()
            self._subscription_service = SubscriptionService(uow=uow)
        return self._subscription_service

    @property
    async def wb_service(self) -> WBService:
        if self._wb_service is None:
            uow = await self.create_uow()
            self._wb_service = WBService(
                uow=uow,
                i18n=self._i18n,  # Используем _i18n
                notification_service=self.notification_service,
                api_key_service=self.api_key_service,
            )
        return self._wb_service

    @property
    async def broker(self) -> NatsBroker:
        if self._broker is None:
            self._broker = broker
        return self._broker
