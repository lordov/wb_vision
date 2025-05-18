from fluentogram import TranslatorHub

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
            i18n: TranslatorHub,
            notification_service: NotificationService,
            api_key_service: ApiKeyService
    ):
        self.uow = uow
        self.api_key_service = api_key_service
        self.notification_service = notification_service
        self.i18n = i18n.get_translator_by_locale('ru')

    async def fetch_and_save_orders(self, user_id: int, api_key: str) -> list[OrderWBCreate] | None:
        """Получение заказов WB, сохранение в БД и формирование уведомлений по новым заказам."""
        api_client = WBAPIClient(token=api_key)
        orders = await api_client.get_orders(user_id)

        if not orders:
            return
        texts = []
        async with self.uow as uow:
            # Сохраняем только новые заказы, возвращаем реально вставленные
            new_orders = await self.uow.wb_orders.add_orders_bulk(
                orders=orders
            )
            await self.uow.commit()
            app_logger.info(f"New orders added for {user_id}")

            new_orders = sorted(new_orders, key=lambda x: x.date)

            for orders in new_orders:
                texts.append(await self._generate_text(uow, user_id=user_id, order=orders))

        if not texts:
            app_logger.info(f"No new orders for {user_id}")
            return

        return texts

    async def _generate_text(self, uow: UnitOfWork, user_id: int, order: OrderWBCreate) -> str:
        """Формирует текст уведомления на основе данных заказа."""
        app_logger.info("Generating notification text", user_id=user_id)

        total_price = round(order.total_price *
                            (1 - order.discount_percent / 100))
        order_date = order.date.date()
        
        counter = await uow.wb_orders.get_counter(user_id, order_date)
        amount = await uow.wb_orders.get_amount(user_id, order_date)
        total_today = await uow.wb_orders.get_total_today(
            user_id, order.nm_id, order_date, total_price)
        total_yesterday = await uow.wb_orders.get_total_yesterday(
            user_id, order.nm_id, order_date)

        text = self.i18n.get(
            "order-text",
            date=order.date.strftime("%Y-%m-%d"),
            counter=counter,
            total_price=total_price,
            amount=amount,
            nm_id=order.nm_id,
            discount=order.discount_percent,
            category=order.category,
            subject=order.subject,
            brand=order.brand,
            article=order.supplier_article,
            total_today=total_today,
            total_yesterday=total_yesterday,
            warehouse_text='чюпеп'
        )
        return await self._clean_text(text)

    async def _clean_text(self, text: str) -> str:
        # Удаляем управляющие символы \u2068 (LRI) и \u2069 (PDI). Для переменных Fluenta
        return text.replace('\u2068', '').replace('\u2069', '').replace('\xa0', '')
