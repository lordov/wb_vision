from bot.database.models import Subscription
from datetime import datetime, timedelta
from bot.database.uow import UnitOfWork
from bot.core.config import settings


from datetime import datetime


class SubscriptionService:
    def __init__(self, uow: UnitOfWork):
        self.repo = uow.subscriptions

    async def check_trial(self, user_id: int) -> bool:
        """Проверка, доступен ли пробный период для пользователя."""
        subscription = await self.repo.get_subscription_by_plan(user_id, "trial")
        return subscription is None

    async def has_active_subscription(self, user_id: int) -> bool:
        """Проверяет, есть ли активная подписка у пользователя (не истекла ли)."""
        subscription = await self.repo.get_active_subscription(user_id)
        return subscription is not None and subscription.expires_at > datetime.now()

    async def create_subscription(
            self,
            user_id: int,
            plan: str,
            is_active: bool = True
    ) -> Subscription:
        """Создаем новую подписку для пользователя."""
        expires_at = datetime.now() + timedelta(days=settings.trial_days)
        return await self.repo.create_subscription(user_id, plan, expires_at, is_active)
