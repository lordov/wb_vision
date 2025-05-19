import asyncio
from fluentogram import TranslatorHub

from bot.api.wb import WBAPIClient
from bot.schemas.wb import NotifOrder
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

    async def fetch_and_save_orders(self, user_id: int, api_key: str) -> list[str] | None:
        api_client = WBAPIClient(token=api_key)
        orders = await api_client.get_orders(user_id)

        if not orders:
            return

        async with self.uow as uow:
            new_orders = await self.uow.wb_orders.add_orders_bulk(orders=orders)
            await self.uow.commit()
            app_logger.info(f"New orders added for {user_id}")

            if not new_orders:
                app_logger.info(f"No new orders for {user_id}")
                return
            # Получаем
            await self._get_stats(uow, user_id, new_orders)
            # Сортируем заказы
            new_orders = sorted(new_orders, key=lambda x: x.counter)

            # Генерируем тексты на основе обновлённых заказов
            texts = await self._generate_texts(orders=new_orders)

        return texts

    async def _generate_texts(self, orders: list[NotifOrder]) -> list[str]:
        texts = []

        for order in orders:
            total_price = round(order.total_price *
                                (1 - order.discount_percent / 100))

            text = self.i18n.get(
                "order-text",
                date=order.date.strftime("%Y-%m-%d"),
                counter=order.counter,
                total_price=total_price,
                amount=order.amount,
                nm_id=order.nm_id,
                discount=order.discount_percent,
                category=order.category,
                subject=order.subject,
                brand=order.brand,
                article=order.supplier_article,
                total_today=order.total_today,
                total_yesterday=order.total_yesterday,
                warehouse_text='чюпеп',
            )
            clean_text = await self._clean_text(text)
            texts.append(clean_text)

        return texts

    async def _clean_text(self, text: str) -> str:
        # Удаляем управляющие символы \u2068 (LRI) и \u2069 (PDI). Для переменных Fluenta
        return text.replace('\u2068', '').replace('\u2069', '').replace('\xa0', '')

    async def _get_stats(self, uow: UnitOfWork,  user_id: int, orders: list[NotifOrder]):
        # Получаем все нужные данные для каждого заказа
        for order in orders:
            order_date = order.date.date()
            total_price = round(order.total_price *
                                (1 - order.discount_percent / 100))

            order.counter = await uow.wb_orders.get_counter(user_id, order.id, order_date)
            order.amount = await uow.wb_orders.get_amount(user_id, order.id, order_date)
            order.total_today = await uow.wb_orders.get_total_today(
                user_id, order.id, order.nm_id, order.date, total_price)
            order.total_yesterday = await uow.wb_orders.get_total_yesterday(order.id,
                user_id, order.nm_id, order_date)
