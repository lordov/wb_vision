import secrets
from bot.database.models import Employee, EmployeeInvite, User
from bot.database.uow import UnitOfWork
from bot.core.logging import app_logger
from bot.core.config import settings


class UserService:
    def __init__(
            self,
            uow: UnitOfWork,
    ):
        self.uow = uow
        self.employee = uow.employee
        self.employee_invite = uow.employee_invites
        self.repo_users = uow.users

    async def get_by_user_id(self, user_id: int) -> User | None:
        return await self.repo_users.get_by_user_id(user_id)

    async def generate_employee_invite(self, telegram_id: int) -> str:
        async with self.uow as uow:
            token = secrets.token_hex(16)
            owner = await self.repo_users.get_by_tg_id(telegram_id)
            invate = await self.employee_invite.add_invite(token, owner.id)

            if not invate:
                app_logger.error("Error adding employee invite")
                return None

            await self.uow.commit()
            app_logger.info(
                "generate_employee_invite", owner_id=owner.id, token=token)

            return f"t.me/{settings.bot.username}?start=addstaff_{owner.id}_{token}"

    async def check_invite(self, owner_id: int, token: str) -> EmployeeInvite | None:
        return await self.employee_invite.check_invite(owner_id, token)

    async def check_user_as_employee(self, telegram_id: int) -> EmployeeInvite | None:
        return await self.employee.check_user_as_employee(telegram_id)

    async def add_employee(self, owner_id: int, telegram_id: int, username: str, token: str) -> Employee | None:
        async with self.uow as uow:
            new_employee = await self.employee.add_employee(owner_id, telegram_id, username)
            if new_employee is None:
                return
            await self.employee_invite.set_is_used_link(token)
            app_logger.info(
                "employee.added", owner_id=owner_id, telegram_id=telegram_id, username=username)
            await self.uow.commit()
            return new_employee

    async def add_user(self, telegram_id: int, username: str, locale: str = "ru") -> User | None:
        return await self.repo_users.add_user(telegram_id, username, locale)

    async def get_active_employees(self, telegram_id: int) -> list[Employee] | None:
        owner = await self.repo_users.get_by_tg_id(telegram_id)
        return await self.employee.get_owners_employees(owner.id)

    async def delete_employee(self, telegram_id: int, employee_id: int) -> None:
        owner = await self.repo_users.get_by_tg_id(telegram_id)
        await self.employee.deactivate_employee(owner.id, employee_id)
        await self.uow.commit()
        app_logger.info(
            "employee.deactivated", owner_id=owner.id, employee_id=employee_id)
