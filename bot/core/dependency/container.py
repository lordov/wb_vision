from typing import Type, TypeVar, Callable
from aiogram import Bot
from cryptography.fernet import Fernet
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.uow import UnitOfWork
from bot.services.api_key import ApiKeyService
from bot.services.subscription import SubscriptionService
from bot.services.notifications import NotificationService
from bot.services.wb_service import WBService

T = TypeVar("T")

class DependencyContainer:
    def __init__(
        self,
        bot_token: str,
        i18n: TranslatorRunner,
        fernet: Fernet,
        session_maker: Callable[[], AsyncSession],
    ) -> None:
        self._bot_token = bot_token
        self._fernet = fernet
        self._session_maker = session_maker
        self._i18n = i18n

        self._bot: Bot | None = None
        self._services: dict[Type, object] = {}

    @property
    def bot(self) -> Bot:
        if self._bot is None:
            self._bot = Bot(token=self._bot_token)
        return self._bot

    async def create_uow(self) -> UnitOfWork:
        return UnitOfWork(self._session_maker())

    async def get(self, service_type: Type[T]) -> T:
        if service_type in self._services:
            return self._services[service_type]

        instance = await self._build(service_type)
        self._services[service_type] = instance
        return instance

    async def _build(self, service_type: Type[T]) -> T:
        if service_type is NotificationService:
            return NotificationService(bot=self.bot)

        elif service_type is ApiKeyService:
            uow = await self.create_uow()
            return ApiKeyService(uow=uow, fernet=self._fernet)

        elif service_type is SubscriptionService:
            uow = await self.create_uow()
            return SubscriptionService(uow=uow)

        elif service_type is WBService:
            uow = await self.create_uow()
            notification_service = await self.get(NotificationService)
            api_key_service = await self.get(ApiKeyService)
            return WBService(
                uow=uow,
                i18n=self._i18n,
                notification_service=notification_service,
                api_key_service=api_key_service,
            ) 

        raise ValueError(f"Unknown service: {service_type}")
