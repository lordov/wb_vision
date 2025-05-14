from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from fluentogram import TranslatorRunner, TranslatorHub
from bot.database.uow import UnitOfWork
from bot.schemas.wb import OrderWBCreate
from bot.core.logging import app_logger


class NotificationService:
    def __init__(
            self,
            uow: UnitOfWork,
            i18n: TranslatorHub,
            bot: Bot
    ):
        self.uow = uow
        self.bot = bot
        self.i18n = i18n.get_translator_by_locale('ru')

    async def send_message(
            self, 
            user_id: int,
            telegram_id: int,
            orders: list[OrderWBCreate]
            ) -> None:
        for order in orders:
            text = await self._generate_text(user_id, order)
            try:
                app_logger.info("Sending notification", user_id=user_id)
                await self.bot.send_photo(
                    chat_id=telegram_id,
                    photo=await self._get_photo(order.nm_id),
                    caption=text, parse_mode="HTML"
                )

            except TelegramForbiddenError:
                ...
            except Exception as e:
                print(e)

    async def _generate_text(self, user_id: int, order: OrderWBCreate) -> str:
        """Формирует текст уведомления на основе данных заказа."""
        app_logger.info("Generating notification text", user_id=user_id)

        order_date = order.date.date()
        total_price = round(order.total_price *
                            (1 - order.discount_percent / 100))
        async with self.uow:
            counter = await self.uow.wb_orders.get_counter(user_id, order_date)
            amount = await self.uow.wb_orders.get_amount(user_id, order_date)
            total_today = await self.uow.wb_orders.get_total_today(
                user_id, order.nm_id, order_date, total_price)
            total_yesterday = await self.uow.wb_orders.get_total_yesterday(
                user_id, order.nm_id, order_date)

        text = self.i18n.get(
            "order-text",
            date=order_date.strftime("%Y-%m-%d"),
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

    async def _get_photo(self, nm_id: int):
        "Находим фотку на вб"
        url = f"https://basket-12.wbbasket.ru/vol1711/part171150/171150581/images/c516x688/1.webp"
        return url

    async def _clean_text(self, text: str) -> str:
        # Удаляем управляющие символы \u2068 (LRI) и \u2069 (PDI). Для переменных Fluenta
        return text.replace('\u2068', '').replace('\u2069', '').replace('\xa0', '')
