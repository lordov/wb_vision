from aiogram_dialog import DialogManager, ShowMode
from aiogram.types import Message, CallbackQuery
from aiogram_dialog.widgets.kbd import Button

from fluentogram import TranslatorRunner

from bot.core.dependency.container import DependencyContainer
from bot.database.uow import UnitOfWork
from bot.services.users import UserService
from bot.core.logging import app_logger
from bot.handlers.states import Employee


async def delete_employee(
    message: Message,
    button: Button,
    dialog_manager: DialogManager
    ):
    container: DependencyContainer = dialog_manager.middleware_data["container"]
    i18n: TranslatorRunner = dialog_manager.middleware_data["i18n"]
    user = message.from_user

    user_service = await container.get(UserService)
    await user_service.delete_employee(user.id, button.widget_id)

    await message.answer(i18n.get("employee-deleted"))

