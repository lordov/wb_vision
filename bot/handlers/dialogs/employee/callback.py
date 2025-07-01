from aiogram_dialog import DialogManager
from aiogram.types import Message
from aiogram_dialog.widgets.kbd import Button

from fluentogram import TranslatorRunner

from bot.core.dependency.container import DependencyContainer
from bot.services.users import UserService
from bot.database.uow import UnitOfWork


async def delete_employee_clbc(
    message: Message,
    button: Button,
    dialog_manager: DialogManager,
    selected_item_id: int,  # это employee_id
):
    container: DependencyContainer = dialog_manager.middleware_data["container"]
    i18n: TranslatorRunner = dialog_manager.middleware_data["i18n"]
    uow: UnitOfWork = dialog_manager.middleware_data["uow"]
    tg_id = message.from_user.id

    user_service = container.get_user_service(uow)
    await user_service.delete_employee(tg_id, int(selected_item_id))

    await message.answer(i18n.get("employee-deleted"))
