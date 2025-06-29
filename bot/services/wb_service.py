from datetime import datetime, timedelta
from fluentogram import TranslatorHub

from bot.api.wb import WBAPIClient
from bot.api.base_api_client import UnauthorizedUser
from bot.schemas.wb import NotifOrder
from bot.services.api_key import ApiKeyService
from bot.database.uow import UnitOfWork
from bot.core.logging import app_logger
from ..services.notifications import NotificationService


BASKET_THRESHOLDS = [
    143, 287, 431, 719, 1007, 1061, 1115, 1169, 1313, 1601,
    1655, 1919, 2045, 2189, 2405, 2621, 2837, 3053, 3269,
    3485, 3701, 3917, 4133, 4349, 4565
]


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
        try:
            api_client = WBAPIClient(token=api_key)
            date_from = (datetime.now() - timedelta(days=1)
                         ).strftime("%Y-%m-%d")
            orders = await api_client.get_orders(user_id, date_from)

            if not orders:
                return

            new_orders = await self.uow.wb_orders.add_orders_bulk(orders=orders)
            app_logger.info(
                f"{len(new_orders)} new orders added for {user_id} ")

            if not new_orders:
                app_logger.info(f"No new orders for {user_id}")
                return

            await self._get_stats(self.uow, user_id, new_orders)

            # Сортируем заказы
            new_orders = sorted(new_orders, key=lambda x: x.counter)

            # Генерируем тексты на основе обновлённых заказов
            texts = await self._generate_texts(orders=new_orders)

            return texts

        except UnauthorizedUser as e:
            app_logger.warning(
                f"API key unauthorized for user {user_id}: {e.message}")

            # Деактивируем API ключ
            await self.api_key_service.handle_unauthorized_key(user_id)

            # Получаем telegram_id пользователя для отправки уведомления
            user = await self.uow.users.get_by_user_id(user_id)
            if user:
                # Отправляем уведомление пользователю
                await self.notification_service.notify_api_key_deactivated(user.telegram_id)

            # Повторно выбрасываем исключение для обработки на верхнем уровне
            raise

    async def pre_load_orders(self, user_id: int, api_key: str) -> None:
        try:
            api_client = WBAPIClient(token=api_key)
            date_from = datetime.now() - timedelta(days=90)
            orders = await api_client.get_orders(user_id, date_from)

            await self.uow.wb_orders.add_orders_bulk(orders=orders)
            app_logger.info(
                f"Pre-loaded orders: {user_id} {len(orders)} ")

        except UnauthorizedUser as e:
            app_logger.warning(
                f"API key unauthorized during pre-load for user {user_id}: {e.message}")
            await self.api_key_service.handle_unauthorized_key(user_id)

    async def load_stocks(self, user_id: int, api_key: str) -> None:
        try:
            api_client = WBAPIClient(token=api_key)
            stocks = await api_client.get_stocks(user_id)

            await self.uow.wb_stocks.add_stocks_bulk(stocks=stocks)
            app_logger.info(f"Loaded stocks: {user_id} {len(stocks)} ")

        except UnauthorizedUser as e:
            app_logger.warning(
                f"API key unauthorized during stock loading for user {user_id}: {e.message}")
            await self.api_key_service.handle_unauthorized_key(user_id)
            raise

    async def _generate_texts(self, orders: list[NotifOrder]) -> list[dict]:
        result = []

        for order in orders:
            total_price = round(order.total_price *
                                (1 - order.discount_percent / 100))

            text = self.i18n.get(
                "order-text",
                date=order.date.strftime("%Y-%m-%d %H:%M"),
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
                logistic=f"{order.warehouse_name}➡{order.region_name}",
                warehouse_text=order.stocks,
            )
            clean_text = await self._clean_text(text)

            photo = await self._get_photo(order.nm_id)

            # Создаем словарь с текстом и фото
            order_data = {
                "text": clean_text,
                "photo": photo  # может быть None, если фото нет
            }

            result.append(order_data)

        return result

    async def _clean_text(self, text: str) -> str:
        # Удаляем управляющие символы \u2068 (LRI) и \u2069 (PDI). Для переменных Fluenta
        return text.replace('\u2068', '').replace('\u2069', '').replace('\xa0', '')

    async def _get_stats(self, uow: UnitOfWork,  user_id: int, orders: list[NotifOrder]):
        # Получаем все нужные данные для каждого заказа
        for order in orders:
            order_date = order.date.date()
            total_price = round(order.total_price *
                                (1 - order.discount_percent / 100))

            order.counter, order.amount = await uow.wb_orders.counter_and_amount(user_id, order.id, order_date)

            order.total_today, order.total_yesterday = await uow.wb_orders.get_totals_combined(
                user_id, order.id, order.nm_id, order.date, total_price)
            order.stocks = await uow.wb_stocks.stock_stats(user_id, order.nm_id)

    async def _get_photo(self, nm_id: int):
        photo_url = await self._get_working_photo_url(nm_id)
        if photo_url is None:
            app_logger.info(f"Photo not found for {nm_id}")
            return None
        return photo_url

    async def _get_working_photo_url(self, nm_id: int) -> str:
        api_client = WBAPIClient()
        estimated = int(await self._get_estimated_basket(nm_id))

        for basket in range(estimated, 31):  # Проверяем с "предположенного" до 30
            url = await self._build_url(nm_id, f"{basket:02}")
            response = await api_client.head_request(url)
            if response:
                return url
        return None

    async def _get_estimated_basket(self, nm_id: int) -> str:
        s = nm_id // 100000
        for i, max_val in enumerate(BASKET_THRESHOLDS, start=1):
            if s <= max_val:
                return f"{i:02}"
        return "26"

    async def _build_url(self, nm_id: int, basket: str) -> str:
        short_id = nm_id // 100000
        return f"https://basket-{basket}.wbbasket.ru/vol{short_id}/part{nm_id // 1000}/{nm_id}/images/big/1.webp"
