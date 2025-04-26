from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from .repositories.wb_repo import WBRepository
from .repositories.base import SQLAlchemyRepository
from .repositories.user import UserRepository
from .repositories.subscription import SubscriptionRepository
from .repositories.api_key import WbApiKeyRepository
from .models import OrdersWB, Payment, Employee


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.api_keys = WbApiKeyRepository(session)
        self.subscriptions = SubscriptionRepository(session)
        self.wb_orders = WBRepository(session, OrdersWB)
        
        self.payments = SQLAlchemyRepository[Payment](session, Payment)
        self.employees = SQLAlchemyRepository[Employee](session, Employee)
        

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()

    async def close(self):
        await self.session.close()


@asynccontextmanager
async def get_uow(session: AsyncSession) -> AsyncIterator[UnitOfWork]:
    uow = UnitOfWork(session)
    try:
        yield uow
        await uow.commit()
    except Exception:
        await uow.rollback()
        raise
    finally:
        await uow.close()


if __name__ == '__main__':
    print(f'{__name__} Запущен самостоятельно')
else:
    print(f'{__name__} Запущен как модуль')
