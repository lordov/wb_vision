from aiogram.types import User
from aiogram_dialog import DialogManager
from fluentogram import TranslatorRunner
from bot.core.dependency.container import DependencyContainer
from bot.services.users import UserService


async def employee_start(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    container: DependencyContainer,
    **kwargs
) -> dict:
    user_service = await container.get(UserService)
    employees = await user_service.get_active_employees(event_from_user.id)
    count_employees = len(employees)

    return {
        'back': i18n.get('back-btn'),
        'employee_text': i18n.get('employee-text', count=count_employees),
        'add_btn': i18n.get('add-employee-btn'),
        'delete_btn': i18n.get('delete-employee-btn'),
        'if_employee': count_employees > 0,
        'can_add_employee': count_employees < 3,
    }


async def employee_delete(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    container: DependencyContainer,
    **kwargs
):
    user_service = await container.get(UserService)
    employees = await user_service.get_active_employees(event_from_user.id)
    employee_choices = [(emp.username, emp.id) for emp in employees]

    return {
        'employees': employee_choices,
        'delete_employee_text': i18n.get('delete-employee-text', count=len(employees)),
        'back': i18n.get('back-btn'),
    }


async def employee_link(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    container: DependencyContainer,
    **kwargs
) -> dict:
    user_service = await container.get(UserService)
    link = await user_service.generate_employee_invite(event_from_user.id)
    return {
        'back': i18n.get('back-btn'),
        'add_employee_text': i18n.get('add-employee-text', link=link),
    }
