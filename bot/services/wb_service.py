from fluentogram import TranslatorRunner

from bot.api.wb import WBAPIClient
from bot.schemas.wb import OrderWBCreate
from bot.services.api_key import ApiKeyService
from ..services.notifications import NotificationService
from bot.database.uow import UnitOfWork


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

    async def fetch_and_save_orders(self, user_id: int, api_key: str) -> list[str] | None:
        """Получение заказов WB, сохранение в БД и формирование уведомлений по новым заказам."""
        api_client = WBAPIClient(token=api_key)
        orders_data = await api_client.get_orders()

        if not orders_data:
            return

        # Валидация через Pydantic
        try:
            validated_orders: list[OrderWBCreate] = [
                OrderWBCreate(**order, user_id=user_id) for order in orders_data
            ]
        except Exception as e:
            # Можно залогировать ошибку валидации
            return

        async with self.uow:
            # Сохраняем только новые заказы, возвращаем реально вставленные
            new_orders = await self.uow.wb_orders.add_orders_bulk(
                orders=validated_orders
            )
            await self.uow.commit()

        if not new_orders:
            return

        # Генерируем тексты уведомлений только по новым заказам
        orders_to_send: list[OrderWBCreate] = [
            OrderWBCreate.model_validate(order) for order in new_orders
        ]
        return orders_to_send
