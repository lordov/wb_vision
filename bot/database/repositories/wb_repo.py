from typing import Type
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


from bot.schemas.wb import OrderWBCreate
from ..models import OrdersWB
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
                            'srid', 'supplierArticle', 'isCancel']
        )
        await self.session.execute(stmt)
