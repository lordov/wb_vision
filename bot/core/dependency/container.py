from typing import Type, TypeVar, Callable
from aiogram import Bot
from cryptography.fernet import Fernet
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.uow import UnitOfWork
from bot.services.api_key import ApiKeyService
from bot.services.subscription import SubscriptionService
from bot.services.notifications import NotificationService
from bot.services.users import UserService
from bot.services.wb_service import WBService
from bot.services.task_control import TaskControlService

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

    @property
    def bot(self) -> Bot:
        if self._bot is None:
            self._bot = Bot(token=self._bot_token)
        return self._bot

    async def create_uow(self) -> UnitOfWork:
        """Создает новый UoW для использования вне middleware (например, в брокерах)."""
        return UnitOfWork(self._session_maker())

    def get_notification_service(self, uow: UnitOfWork) -> NotificationService:
        """Создает NotificationService с переданным UoW."""
        return NotificationService(uow=uow, i18n=self._i18n, bot=self.bot)

    def get_api_key_service(self, uow: UnitOfWork) -> ApiKeyService:
        """Создает ApiKeyService с переданным UoW."""
        return ApiKeyService(uow=uow, fernet=self._fernet)

    def get_subscription_service(self, uow: UnitOfWork) -> SubscriptionService:
        """Создает SubscriptionService с переданным UoW."""
        return SubscriptionService(uow=uow)

    def get_wb_service(self, uow: UnitOfWork) -> WBService:
        """Создает WBService с переданным UoW."""
        notification_service = self.get_notification_service(uow)
        api_key_service = self.get_api_key_service(uow)
        return WBService(
            uow=uow,
            i18n=self._i18n,
            notification_service=notification_service,
            api_key_service=api_key_service,
        )

    def get_user_service(self, uow: UnitOfWork) -> UserService:
        """Создает UserService с переданным UoW."""
        return UserService(uow=uow)
        
    def get_task_control_service(self, uow: UnitOfWork) -> TaskControlService:
        """Создает TaskControlService с переданным UoW."""
        return TaskControlService(uow=uow)

    # Deprecated methods - оставляем для обратной совместимости
    async def get(self, service_type: Type[T]) -> T:
        """Deprecated: используйте get_*_service методы с явным UoW."""
        if service_type in [NotificationService, ApiKeyService, SubscriptionService, 
                           WBService, UserService, TaskControlService]:
            raise ValueError(
                f"Service {service_type.__name__} requires UoW. "
                f"Use get_{service_type.__name__.lower().replace('service', '_service')} method instead."
            )
        raise ValueError(f"Unknown service: {service_type}")

    async def _build(self, service_type: Type[T]) -> T:
        """Deprecated: используйте get_*_service методы с явным UoW."""
        raise ValueError("This method is deprecated. Use get_*_service methods instead.")
