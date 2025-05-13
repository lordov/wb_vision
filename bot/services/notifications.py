from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from fluentogram import TranslatorRunner
from bot.database.uow import UnitOfWork
from bot.schemas.wb import OrderWBCreate


class NotificationService:
    def __init__(
            self,
            uow: UnitOfWork,
            i18n: TranslatorRunner,
            bot: Bot
    ):
        self.uow = uow
        self.bot = bot
        self.i18n = i18n

    async def send_message(self, user_id: int, orders: list[OrderWBCreate]) -> None:
        for order in orders:
            text = await self._generate_text(user_id, order)
            try:
                await self.bot.send_photo(
                    chat_id=user_id,
                    photo=await self._get_photo(order.nm_id),
                    caption=text
                )

            except TelegramForbiddenError:
                ...
            except Exception as e:
                print(e)

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

    async def _get_photo(self, nm_id: int):
        "Находим фотку на вб"
        url = f"https://basket-12.wbbasket.ru/vol1711/part171150/171150581/images/c516x688/1.webp",
        return url
