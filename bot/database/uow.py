from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from .repositories.wb_repo import WBRepository
from .repositories.base import SQLAlchemyRepository
from .repositories.user import UserRepository
from .repositories.subscription import SubscriptionRepository
from .repositories.api_key import WbApiKeyRepository
from .repositories.employee import EmployeeRepository
from .repositories.task_status import TaskStatusRepository
from .models import (
    EmployeeInvite, OrdersWB, Payment, Employee,
    SalesWB, StocksWB, TaskStatus
)
from bot.core.logging import db_logger


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._closed = False
        self.users = UserRepository(session)
        self.api_keys = WbApiKeyRepository(session)
        self.subscriptions = SubscriptionRepository(session)
        self.wb_orders = WBRepository(session, OrdersWB)
        self.wb_sales = WBRepository(session, SalesWB)
        self.wb_stocks = WBRepository(session, StocksWB)
        self.employee = EmployeeRepository(session, Employee)
        self.employee_invites = EmployeeRepository(session, EmployeeInvite)
        self.task_status = TaskStatusRepository(session, TaskStatus)

        self.payments = SQLAlchemyRepository[Payment](session, Payment)

    async def commit(self):
        """Коммит транзакции."""
        if not self._closed and self.session.is_active:
            await self.session.commit()
            db_logger.debug("Transaction committed")

    async def rollback(self):
        """Откат транзакции."""
        if not self._closed and self.session.is_active:
            await self.session.rollback()
            db_logger.debug("Transaction rolled back")

    async def close(self):
        """Закрытие сессии."""
        if not self._closed:
            await self.session.close()
            self._closed = True
            db_logger.debug("Session closed")

    async def __aenter__(self):
        """Вход в контекстный менеджер."""
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Выход из контекстного менеджера."""
        try:
            if exc_type is not None:
                # Если была ошибка, откатываем транзакцию
                await self.rollback()
                db_logger.error(f"Exception in UoW context: {exc_type.__name__}: {exc}")
            else:
                # Если ошибок не было, коммитим
                await self.commit()
        except Exception as e:
            db_logger.error(f"Error in UoW __aexit__: {e}")
            try:
                await self.rollback()
            except Exception as rollback_error:
                db_logger.error(f"Error during rollback: {rollback_error}")
        finally:
            await self.close()

if __name__ == '__main__':
    print(f'{__name__} Запущен самостоятельно')
else:
    print(f'{__name__} Запущен как модуль')
