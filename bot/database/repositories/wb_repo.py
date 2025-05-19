from datetime import datetime
from typing import Type
from sqlalchemy import Date, Numeric, cast, func, select
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

    async def get_counter(self, user_id: int, order_id: int, date: datetime.date) -> int:
        """
        Возвращает номер заказа по порядку в рамках дня (счётчик),
        основываясь на id и дате (по полю OrdersWB.date).
        """
        try:
            stmt = select(func.count()).where(
                OrdersWB.user_id == user_id,
                cast(OrdersWB.date, Date) == date,
                OrdersWB.id < order_id,
                OrdersWB.is_cancel.is_(False)
            )
            result = await self.session.execute(stmt)
            count = result.scalar() or 0
            return count + 1  # Текущий заказ — следующий по порядку
        except SQLAlchemyError as e:
            db_logger.error("Error in get_order_day_counter", error=str(e))
            return 1

    async def get_amount(self, user_id: int, order_id: int, date: datetime.date) -> int:
        """Общая сумма заказов за дату (с учетом скидок)."""
        try:
            stmt = select(
                func.sum(
                    OrdersWB.total_price *
                        (1 - OrdersWB.discount_percent / 100)
                ).label("total_amount")
            ).where(
                OrdersWB.user_id == user_id,
                cast(OrdersWB.date, Date) == date,
                OrdersWB.id < order_id,
                OrdersWB.is_cancel.is_(False),
            )
            result = await self.session.execute(stmt)
            total_amount = result.scalar()
            return round(total_amount) if total_amount else 0
        except SQLAlchemyError as e:
            db_logger.error("Error in get_amount", error=str(e))
            return 0

    async def get_total_today(
        self,
        user_id: int,
        order_id: int,
        nm_id: int,
        date: datetime,  # теперь точное время
        total_price: float = 0,
    ) -> str | int:
        try:
            if total_price == 0:
                raise ValueError("Ответ от сервера отдал 0")

            # Начало дня (2025-05-18 00:00:00)
            start_of_day = datetime.combine(date.date(), datetime.min.time())

            # Запрос по диапазону времени в течение дня
            stmt = (
                select(
                    func.count().label("order_count"),
                    func.sum(OrdersWB.total_price * (1 - OrdersWB.discount_percent / 100)).label("total_price")
                )
                .where(
                    OrdersWB.user_id == user_id,
                    OrdersWB.nm_id == nm_id,
                    OrdersWB.is_cancel == False,
                    OrdersWB.date >= start_of_day,
                    OrdersWB.date <= date
                )
            )

            result = await self.session.execute(stmt)
            order_count, db_total_price = result.fetchone()

            # Если заказов нет, используем переданный total_price
            if order_count == 1 or db_total_price is None:
                final_total = total_price
            else:
                final_total = db_total_price + total_price

            return f"{order_count} на {round(final_total)}"

        except ValueError as ve:
            db_logger.warning(f"Warning: {ve}")
            return 0
        except (SQLAlchemyError, Exception) as e:
            db_logger.error(f"Error in get_total_today: {e}")
            return 0
        
    async def get_total_yesterday(
        self, order_id: int, user_id: int, nm_id: int, date: str) -> str:
        """
        Получает количество заказов и общую сумму за указанный nmId и дату.
        """
        try:

            # Запрос для фильтрации по nmId и дате, подсчёта заказов и суммы
            stmt = (
                select(
                    func.count().label("order_count"),
                    func.sum(
                        cast(
                            OrdersWB.total_price, Numeric
                        ) * (1 - cast(OrdersWB.discount_percent, Numeric) / 100)).label("total_price")
                )
                .where(
                    OrdersWB.user_id == user_id,
                    OrdersWB.nm_id == nm_id,
                    OrdersWB.is_cancel == False,
                    OrdersWB.id < order_id,
                    cast(OrdersWB.date, Date) == date
                )
            )

            # Выполнение запроса
            result = await self.session.execute(stmt)
            order_count, total_price = result.fetchone()
            if total_price is None:
                total_price = 0

            # Формирование результата
            return f"{order_count} на {round(total_price)}"

        except (SQLAlchemyError, Exception) as e:
            db_logger.error(f"Error in get_totals_yesterday: {e}")
            return 0
