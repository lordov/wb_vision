from aiogram_dialog import DialogManager, ShowMode
from aiogram.types import Message, CallbackQuery
from aiogram_dialog.widgets.kbd import Button

from fluentogram import TranslatorRunner

from bot.core.dependency.container import DependencyContainer
from bot.database.uow import UnitOfWork
from bot.services.users import UserService
from bot.core.logging import app_logger
from bot.handlers.states import Employee


async def delete_employee_clbc(
    message: Message,
    button: Button,
    dialog_manager: DialogManager,
    selected_item_id: int,  # это employee_id
    ):
    container: DependencyContainer = dialog_manager.middleware_data["container"]
    i18n: TranslatorRunner = dialog_manager.middleware_data["i18n"]
    tg_id = message.from_user.id

    user_service = await container.get(UserService)
    await user_service.delete_employee(tg_id, int(selected_item_id))

    await message.answer(i18n.get("employee-deleted"))

