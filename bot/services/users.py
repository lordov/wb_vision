import secrets
from bot.database.models import EmployeeInvite
from bot.database.uow import UnitOfWork
from bot.core.logging import app_logger
from bot.core.config import settings


class UserService:
    def __init__(
            self,
            uow: UnitOfWork,
    ):
        self.employee = uow.employees
        self.employee_invite = uow.employee_invites
        self.repo_users = uow.users

    async def generate_employee_invite(self, owner_id: int) -> str:
        token = secrets.token_hex(16)
        invate = await self.employee_invite.add_invite(token, owner_id)

        if not invate:
            app_logger.error("Error adding employee invite")
            return None
        
        app_logger.info(
            "generate_employee_invite", owner_id=owner_id, token=token)
        return f"t.me/{settings.bot.username}?start=addstaff_{owner_id}_{token}"

    async def check_invite(self, owner_id: int, token: str) -> EmployeeInvite | None:
        return await self.employee_invite.check_invite(owner_id, token)

    async def check_user_as_employee(self, telegram_id: int) -> EmployeeInvite | None:
        return await self.employee.check_user_as_employee(telegram_id)

    async def add_employee(self, owner_id: int, telegram_id: int, username: str, token: str) -> EmployeeInvite | None:
        new_employee = await self.employee.add_employee(owner_id, telegram_id, username)
        if new_employee is None:
            return
        await self.employee_invite.set_is_used_link(token)
        app_logger.info(
            "employee.added", owner_id=owner_id, telegram_id=telegram_id, username=username)
        return
    
    async def add_user(self, telegram_id: int, username: str, locale: str = "ru") -> EmployeeInvite | None:
        return await self.repo_users.get_or_create(telegram_id, username, locale)
