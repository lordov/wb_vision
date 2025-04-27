from fluentogram import TranslatorRunner

from bot.api.wb import WBAPIClient
from bot.schemas.wb import OrderWBCreate
from bot.services.api_key import ApiKeyService
from ..services.notifications import NotificationService
from bot.database.uow import UnitOfWork
from bot.core.security import fernet


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

    async def fetch_and_save_orders(self, user_id: int, api_key: str) -> None:
        """Получение заказов WB и сохранение в БД + отправка уведомлений."""
        active_key = await self.api_key_service.get_all_decrypted_keys()
        api_client = WBAPIClient(token=api_key)
        orders_data = await api_client.get_orders()

        if not orders_data:
            return

        # Валидация через Pydantic
        try:
            validated_orders: list[OrderWBCreate] = [
                OrderWBCreate(**order) for order in orders_data]
        except Exception as e:
            # Тут можно логировать ошибку валидации
            return

        async with self.uow:
            await self.uow.wb_orders.add_orders_bulk(user_id=user_id, orders=validated_orders)
            await self.uow.commit()

        # Отправляем уведомления
        for order in validated_orders:
            text = await self._generate_text(order)
            await self.notification_service.send_message(user_id, text)

    async def _generate_text(self, user_id: int, order: OrderWBCreate) -> str:
        """Формирует текст уведомления на основе данных заказа."""
        order_date = order.date.date()

        async with self.uow:
            today_counter = await self.uow.wb_orders.get_counter(user_id, order_date)
            today_amount = await self.uow.wb_orders.get_amount(user_id, order_date)

        text = self.i18n.get(
            barcode=order.barcode,
            subject=order.subject,
            size=order.tech_size,
            warehouse=order.warehouse_name,
            price=int(order.total_price),
            today_cntr=today_counter,
            amount=today_amount,
        )
        return text
