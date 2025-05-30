from typing import Type
from datetime import datetime, timedelta
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from bot.database.models import Employee, EmployeeInvite
from .base import SQLAlchemyRepository, T
from bot.core.logging import db_logger


class EmployeeRepository(SQLAlchemyRepository[Employee]):
    def __init__(self, session: AsyncSession, model: Type[T]):
        super().__init__(session, model)

    async def get_by_owner_id(self, owner_id: int) -> Employee | None:
        """Получаем активных сотрудников."""
        stmt = select(Employee).where(
            Employee.owner_id == owner_id,
            Employee.is_active,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, owner_id: int, telegram_id: int) -> Employee | None:
        stmt = select(Employee).where(
            Employee.telegram_id == telegram_id,
            Employee.owner_id == owner_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_employee(
            self,
            owner_id: int,
            telegram_id: int,
            username: str,
    ) -> Employee:
        employee = await self.get_by_telegram_id(telegram_id, owner_id)
        if employee:
            if not employee.is_active:
                employee.is_active = True
                db_logger.info(
                    "employee.reactivated", owner_id=owner_id, telegram_id=telegram_id)
                return employee

        # Добавляем сотрудника
        new_employee = Employee(
            owner_id=owner_id,
            telegram_id=telegram_id,
            username=username,
        )
        try:
            self.session.add(new_employee)
            db_logger.info(
                "employee.created", owner_id=owner_id, telegram_id=telegram_id)
        except SQLAlchemyError as e:
            db_logger.error(
                "employee.create.failed", owner_id=owner_id, error=str(e))
            raise
        return new_employee

    async def add_invite(self, token, owner_id: int) -> EmployeeInvite:
        """Создаем новую подписку."""
        employee_invite = EmployeeInvite(
            token=token,
            owner_id=owner_id,
        )
        self.session.add(employee_invite)
        db_logger.info("employee.invite.created", owner_id=owner_id)
        return employee_invite

    async def get_by_token(self, token: str) -> EmployeeInvite | None:
        stmt = select(EmployeeInvite).where(EmployeeInvite.token == token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def check_invite(self, owner_id: int, token: str) -> EmployeeInvite | None:
        # Проверка инвайта
        stmt = select(EmployeeInvite).where(
            EmployeeInvite.token == token,
            EmployeeInvite.owner_id == owner_id,
            EmployeeInvite.is_used == False,
            EmployeeInvite.created >= datetime.now() - timedelta(hours=3)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def check_user_as_employee(self, telegram_id: int) -> Employee | None:
        # Проверка: не был ли уже добавлен сотрудник
        stmt = select(Employee).where(
            Employee.telegram_id == telegram_id,
            Employee.is_active == True
        )
        try:
            result = await self.session.execute(stmt)
            employee = result.scalar_one_or_none()
        except SQLAlchemyError as e:
            db_logger.error(
                "employee.lookup.failed", telegram_id=telegram_id, error=str(e))
        return employee

    async def set_is_used_link(self, token: str) -> None:
        stmt = select(EmployeeInvite).where(EmployeeInvite.token == token)
        try:
            result = await self.session.execute(stmt)
            employee_invite = result.scalar_one_or_none()
        except SQLAlchemyError as e:
            db_logger.error(
                "employee.invite.lookup.failed", token=token, error=str(e)
            )
        employee_invite.is_used = True
        db_logger.info("employee.invite.used", token=token)

    async def get_owners_employees(self, owner_id: int) -> list[Employee] | None:
        """
        Get all active employees of given owner.

        Args:
            owner_id: Integer id of the owner.

        Returns:
            List of Employee objects or None.
        """
        stmt = select(Employee).where(
            Employee.owner_id == owner_id,
            Employee.is_active
        )
        try:
            result = await self.session.execute(stmt)
            employeers = result.scalars().all()
        except SQLAlchemyError as e:
            db_logger.error(
                "employee.fetching.failed", owner_id=owner_id, error=str(e))
        return employeers

    async def deactivate_employee(self, owner_id: int, telegram_id: int) -> None:
        stmt = select(Employee).where(
            Employee.telegram_id == telegram_id,
            Employee.owner_id == owner_id
        )
        try:
            result = await self.session.execute(stmt)
            employee = result.scalar_one_or_none()
        except SQLAlchemyError as e:
            db_logger.error(
                "employee.deactivate.failed", owner_id=owner_id, error=str(e))
        employee.is_active = False
        db_logger.info(
            "employee.deactivated", owner_id=owner_id, telegram_id=telegram_id)
