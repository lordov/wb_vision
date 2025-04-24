from bot.database.repositories.subscription import SubscriptionRepository
from bot.database.models import Subscription
from datetime import datetime, timedelta
from bot.database.uow import UnitOfWork
from bot.core.config import settings


class SubscriptionService:
    def __init__(self, uow: UnitOfWork):
        self.repo = uow.subscriptions

    async def check_trial(self, user_id: int) -> bool:
        """Проверка, доступен ли пробный период для пользователя."""
        subscription = await self.repo.get_subscription_by_plan(user_id, "trial")
        return subscription is None

    async def get_active_subscription(self, user_id: int) -> Subscription | None:
        """Получаем активную подписку пользователя."""
        return await self.repo.get_active_subscription(user_id)

    async def create_subscription(self, user_id: int, plan: str) -> Subscription:
        """Создаем новую подписку для пользователя."""
        expires_at = datetime.now() + timedelta(days=settings.trial_days)
        return await self.repo.create_subscription(user_id, plan, expires_at)
