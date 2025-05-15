from fluentogram import TranslatorRunner

from bot.api.wb import WBAPIClient
from bot.schemas.wb import OrderWBCreate
from bot.services.api_key import ApiKeyService
from bot.database.uow import UnitOfWork
from bot.core.logging import app_logger
from ..services.notifications import NotificationService


class WBService:
    def __init__(
            self,
            uow: UnitOfWork,
            i18n: TranslatorRunner,
            notification_service: NotificationService,
            api_key_service: ApiKeyService
    ):
        self.uow = uow
        self.api_key_service = api_key_service
        self.notification_service = notification_service
        self.i18n = i18n

    async def fetch_and_save_orders(self, user_id: int, api_key: str) -> list[OrderWBCreate] | None:
        """Получение заказов WB, сохранение в БД и формирование уведомлений по новым заказам."""
        api_client = WBAPIClient(token=api_key)
        orders = await api_client.get_orders(user_id)

        if not orders:
            return

        async with self.uow:
            # Сохраняем только новые заказы, возвращаем реально вставленные
            new_orders = await self.uow.wb_orders.add_orders_bulk(
                orders=orders
            )
            await self.uow.commit()
            app_logger.info(f"New orders added for {user_id}")

        if not new_orders:
            app_logger.info(f"No new orders for {user_id}")
            return

        return new_orders
