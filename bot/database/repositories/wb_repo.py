from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Type
from sqlalchemy import Date, Numeric, cast, func, literal_column, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from bot.core.logging import db_logger

from bot.schemas.wb import NotifOrder, OrderWBCreate, SalesWBCreate, StocksWBCreate
from ..models import OrdersWB, StocksWB, SalesWB
from ..repositories.base import SQLAlchemyRepository
from .base import T


class WBRepository(SQLAlchemyRepository[OrdersWB]):
    def __init__(self, session: AsyncSession, model: Type[T]):
        super().__init__(session, model)

    async def add_orders_bulk(self, orders: list[OrderWBCreate]) -> list[NotifOrder]:
        """Добавить заказы по одному для проверки."""
        db_logger.info("add_orders_bulk", count=len(orders))
        if not orders:
            return []

        new_orders = []
        for order in orders:
            data = order.model_dump()
            stmt = (
                insert(OrdersWB)
                .values(data)
                .on_conflict_do_nothing(
                    index_elements=['date', 'user_id', 'srid',
                                    'nm_id', 'is_cancel', 'tech_size']
                )
                .returning(OrdersWB)
            )
            try:
                result = await self.session.execute(stmt)
                inserted_order = result.scalar_one_or_none()
                if inserted_order:
                    new_orders.append(inserted_order)
            except SQLAlchemyError as e:
                db_logger.error("Error in add_orders_bulk", error=str(e))

        return [NotifOrder.model_validate(order) for order in new_orders]

    async def add_sales_bulk(self, orders: list[SalesWBCreate]) -> None:
        """Добавить продажи пачкой"""
        if not orders:
            return

        data = [order.model_dump(by_alias=True) for order in orders]

        stmt = insert(SalesWB).values(data)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=['date', 'user_id',
                            'srid', 'nm_id', 'isCancel', 'tech_size']
        )
        await self.session.execute(stmt)

    async def add_stocks_bulk(self, orders: list[StocksWBCreate]) -> None:
        """Добавить продажи пачкой"""
        if not orders:
            return

        data = [order.model_dump(by_alias=True) for order in orders]

        stmt = insert(StocksWB).values(data)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=['import_date', 'user_id',
                            'warehouse_name', 'nm_id', 'tech_size']
        )
        await self.session.execute(stmt)

    async def counter_and_amount(self, user_id: int, order_id: int, date: datetime.date) -> int:
        """
        Возвращает номер заказа по порядку в рамках дня (счётчик),
        основываясь на id и дате (по полю OrdersWB.date).
        """
        try:
            stmt = select(
                func.count().label('order_count'),
                func.sum(
                    OrdersWB.total_price *
                        (1 - OrdersWB.discount_percent / 100)
                ).label("total_amount")
            ).where(
                OrdersWB.user_id == user_id,
                cast(OrdersWB.date, Date) == date,
                OrdersWB.id < order_id,
                OrdersWB.is_cancel.is_(False)
            )
            result = await self.session.execute(stmt)
            # или `result.first()`, если возможна пустая строка
            order_count, total_amount = result.one()
            total_amount = round(total_amount) if total_amount else 0
            return order_count + 1, total_amount

        except SQLAlchemyError as e:
            db_logger.error("Error in get_order_day_counter", error=str(e))
            return 1

    # async def get_amount(self, user_id: int, order_id: int, date: datetime.date) -> int:
    #     """Общая сумма заказов за дату (с учетом скидок)."""
    #     try:
    #         stmt = select(
    #             func.sum(
    #                 OrdersWB.total_price *
    #                     (1 - OrdersWB.discount_percent / 100)
    #             ).label("total_amount")
    #         ).where(
    #             OrdersWB.user_id == user_id,
    #             cast(OrdersWB.date, Date) == date,
    #             OrdersWB.id < order_id,
    #             OrdersWB.is_cancel.is_(False),
    #         )
    #         result = await self.session.execute(stmt)
    #         total_amount = result.scalar()
    #         return round(total_amount) if total_amount else 0
    #     except SQLAlchemyError as e:
    #         db_logger.error("Error in get_amount", error=str(e))
    #         return 0

    # async def get_total_today(
    #     self,
    #     user_id: int,
    #     order_id: int,
    #     nm_id: int,
    #     date: datetime,  # теперь точное время
    #     total_price: float = 0,
    # ) -> str | int:
    #     try:
    #         if total_price == 0:
    #             raise ValueError("Ответ от сервера отдал 0")

    #         # Начало дня (2025-05-18 00:00:00)
    #         start_of_day = datetime.combine(date.date(), datetime.min.time())

    #         # Запрос по диапазону времени в течение дня
    #         stmt = (
    #             select(
    #                 func.count().label("order_count"),
    #                 func.sum(OrdersWB.total_price * (1 -
    #                          OrdersWB.discount_percent / 100)).label("total_price")
    #             )
    #             .where(
    #                 OrdersWB.user_id == user_id,
    #                 OrdersWB.nm_id == nm_id,
    #                 OrdersWB.is_cancel == False,
    #                 OrdersWB.date >= start_of_day,
    #                 OrdersWB.date <= date
    #             )
    #         )

    #         result = await self.session.execute(stmt)
    #         order_count, db_total_price = result.fetchone()

    #         # Если заказов нет, используем переданный total_price
    #         if order_count == 1 or db_total_price is None:
    #             final_total = total_price
    #         else:
    #             final_total = db_total_price + total_price

    #         return f"{order_count} на {round(final_total)}"

    #     except ValueError as ve:
    #         db_logger.warning(f"Warning: {ve}")
    #         return 0
    #     except (SQLAlchemyError, Exception) as e:
    #         db_logger.error(f"Error in get_total_today: {e}")
    #         return 0

    # async def get_total_yesterday(
    #         self, order_id: int, user_id: int, nm_id: int, date: str) -> str:
    #     """
    #     Получает количество заказов и общую сумму за указанный nmId и дату.
    #     """
    #     try:

    #         # Запрос для фильтрации по nmId и дате, подсчёта заказов и суммы
    #         stmt = (
    #             select(
    #                 func.count().label("order_count"),
    #                 func.sum(
    #                     cast(
    #                         OrdersWB.total_price, Numeric
    #                     ) * (1 - cast(OrdersWB.discount_percent, Numeric) / 100)).label("total_price")
    #             )
    #             .where(
    #                 OrdersWB.user_id == user_id,
    #                 OrdersWB.nm_id == nm_id,
    #                 OrdersWB.is_cancel == False,
    #                 OrdersWB.id < order_id,
    #                 cast(OrdersWB.date, Date) == date
    #             )
    #         )

    #         # Выполнение запроса
    #         result = await self.session.execute(stmt)
    #         order_count, total_price = result.fetchone()
    #         if total_price is None:
    #             total_price = 0

    #         # Формирование результата
    #         return f"{order_count} на {round(total_price)}"

    #     except (SQLAlchemyError, Exception) as e:
    #         db_logger.error(f"Error in get_totals_yesterday: {e}")
    #         return 0

    async def get_totals_combined(
        self,
        user_id: int,
        order_id: int,
        nm_id: int,
        date: datetime,  # точное время
        total_price_today: float = 0,
    ) -> dict:
        try:
            if total_price_today == 0:
                raise ValueError("Ответ от сервера отдал 0")

            start_of_day = datetime.combine(date.date(), datetime.min.time())
            yesterday = date.date() - timedelta(days=1)

            # Подзапрос для сегодняшних данных
            today_subquery = (
                select(
                    func.count().label("order_count"),
                    func.sum(OrdersWB.total_price * (1 -
                                                     OrdersWB.discount_percent / 100)).label("total_price")
                )
                .where(
                    OrdersWB.user_id == user_id,
                    OrdersWB.nm_id == nm_id,
                    OrdersWB.is_cancel == False,
                    OrdersWB.date >= start_of_day,
                    OrdersWB.date <= date
                )
                .subquery()
            )

            # Подзапрос для вчерашних данных
            yesterday_subquery = (
                select(
                    func.count().label("order_count"),
                    func.sum(cast(OrdersWB.total_price, Numeric) * (1 -
                                                                    cast(OrdersWB.discount_percent, Numeric) / 100)).label("total_price")
                )
                .where(
                    OrdersWB.user_id == user_id,
                    OrdersWB.nm_id == nm_id,
                    OrdersWB.is_cancel == False,
                    OrdersWB.id < order_id,
                    cast(OrdersWB.date, Date) == yesterday
                )
                .subquery()
            )

            # Основной запрос через скалярные подзапросы
            stmt = select(
                select(today_subquery.c.order_count).scalar_subquery().label(
                    "today_order_count"),
                select(today_subquery.c.total_price).scalar_subquery().label(
                    "today_total_price"),
                select(yesterday_subquery.c.order_count).scalar_subquery().label(
                    "yesterday_order_count"),
                select(yesterday_subquery.c.total_price).scalar_subquery().label(
                    "yesterday_total_price"),
            )

            result = await self.session.execute(stmt)
            row = result.fetchone()

            # Обработка результатов
            today_orders = row.today_order_count or 0
            today_total = row.today_total_price or 0.0

            if today_orders == 0 or today_total == 0:
                final_today_total = total_price_today
            else:
                final_today_total = today_total + total_price_today

            return f"{today_orders} на {round(final_today_total)}", f"{row.yesterday_order_count or 0} на {round(row.yesterday_total_price or 0)}"

        except ValueError as ve:
            db_logger.warning(f"Warning: {ve}")
            return 0, 0
        except (SQLAlchemyError, Exception) as e:
            db_logger.error(f"Error in get_totals_combined: {e}")
            return 0, 0

    async def stock_stats(self, nm_id: str) -> Optional[str]:
        """
        Получает количество единиц товара на каждом складе по артикулу товара (nmId).
        """
        try:
            # Получаем последнюю дату изменения для данного nmId
            stmt = select(func.max(StocksWB.last_сhange_date)
                          ).where(StocksWB.nm_id == nm_id)
            result = await self.session.execute(stmt)
            last_change_date = result.scalar()

            if not last_change_date:
                return f"Остаток для {nm_id}: 0"

            # Получаем остаток товара на складах на последнюю дату импорта
            stmt = (
                select(StocksWB.warehouse_name, StocksWB.quantity)
                .where(
                    (
                        StocksWB.nm_id == nm_id,
                        StocksWB.quantity != 0,
                        StocksWB.import_date == select(
                            func.max(StocksWB.import_date))
                        .where((StocksWB.nm_id == nm_id, StocksWB.quantity != 0)).scalar_subquery()
                    )
                )
            )
            results = await self.session.execute(stmt)
            stock_data = results.fetchall()

            if not stock_data:
                return f"Остаток для {nm_id}: 0"

            # Получаем общее количество по артикулу на последнюю дату импорта
            stmt = select(func.sum(StocksWB.quantity)).where(
                StocksWB.nm_id == nm_id,
                StocksWB.import_date == select(
                    func.max(StocksWB.ImportDate))
                .where((StocksWB.nm_id == nm_id, StocksWB.quantity != 0)).scalar_subquery()
            )
            result = await self.session.execute(stmt)
            total_quantity = result.scalar() or 0

            # Получаем количество заказов за последние 30 дней
            stmt = select(func.count()).where(
                (
                    OrdersWB.nm_id == nm_id,
                    OrdersWB.date >= func.date_sub(
                        func.now(), text("INTERVAL 30 DAY"))
                )
            )
            result = await self.session.execute(stmt)
            monthly_order_count = result.scalar() or 0

            # Рассчитываем скорость заказов
            order_speed = monthly_order_count / 30 if monthly_order_count else 0
            stock_ratio = round(float(total_quantity) /
                                order_speed) if order_speed > 0 else 0

            # Группируем количество по складам
            warehouse_totals = defaultdict(int)
            for warehouse, quantity in stock_data:
                warehouse_totals[warehouse] += quantity

            # Формируем текст
            output = f'Дата обновления: {last_change_date.strftime("%Y-%m-%d")}\n'
            for warehouse, quantity in warehouse_totals.items():
                output += f"📦 {warehouse} – {quantity} шт.\n"

            output += f'\n📦 Всего: {total_quantity} шт. Хватит на {stock_ratio} дн.'
            return output

        except SQLAlchemyError as e:
            await self.session.rollback()
            db_logger.error(f"Error in stock_stats: {e}")
            return None
