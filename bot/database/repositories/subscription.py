from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from bot.database.models import Subscription
from .base import SQLAlchemyRepository


class SubscriptionRepository(SQLAlchemyRepository[Subscription]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Subscription)

    async def get_active_subscription(self, user_id: int) -> Subscription | None:
        """Получаем активную подписку для пользователя."""
        stmt = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.is_active,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_subscription_by_plan(self, user_id: int, plan: str) -> Subscription | None:
        """Получаем подписку по плану."""
        stmt = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.plan == plan
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_subscription(
            self, 
            user_id: int, 
            plan: str,
            expires_at: datetime,
            is_active: bool = True,
            ) -> Subscription:
        """Создаем новую подписку."""
        subscription = Subscription(
            user_id=user_id, plan=plan, 
            expires_at=expires_at,
            is_active=is_active
            )
        self.session.add(subscription)
        return subscription
