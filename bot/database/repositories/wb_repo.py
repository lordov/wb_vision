from datetime import datetime
from typing import Type
from sqlalchemy import Date, cast, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from bot.core.logging import db_logger

from bot.schemas.wb import OrderWBCreate, SalesWBCreate, StocksWBCreate
from ..models import OrdersWB, StocksWB, SalesWB
from ..repositories.base import SQLAlchemyRepository
from .base import T


class WBRepository(SQLAlchemyRepository[OrdersWB]):
    def __init__(self, session: AsyncSession, model: Type[T]):
        super().__init__(session, model)

    async def add_orders_bulk(self, orders: list[OrderWBCreate]) -> None:
        """Добавить заказы пачкой"""
        if not orders:
            return

        data = [order.model_dump(by_alias=True) for order in orders]

        stmt = insert(OrdersWB).values(data)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=['date', 'user_id',
                            'srid', 'nm_id', 'isCancel', 'tech_size']
        )
        await self.session.execute(stmt)

    async def add_orders_bulk(self, orders: list[SalesWBCreate]) -> None:
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

    async def get_counter(self, user_id: int, date: datetime.date) -> int:
        """Количество заказов за дату."""
        try:
            stmt = select(func.count()).where(
                OrdersWB.user_id == user_id,
                cast(OrdersWB.date, Date) == date,
                OrdersWB.is_cancel.is_(False),
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            db_logger.error("Error in get_counter", error=str(e))
            return 0

    async def get_amount(self, user_id: int, date: datetime.date) -> int:
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
                OrdersWB.is_cancel.is_(False),
            )
            result = await self.session.execute(stmt)
            total_amount = result.scalar()
            return round(total_amount) if total_amount else 0
        except SQLAlchemyError as e:
            db_logger.error("Error in get_amount", error=str(e))
            return 0
