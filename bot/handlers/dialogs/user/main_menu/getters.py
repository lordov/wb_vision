
from aiogram import html
from aiogram.types import User
from aiogram.types import User
from aiogram_dialog import DialogManager
from fluentogram import TranslatorRunner



async def is_admin(dialog_manager: DialogManager, event_from_user: User, **kwargs):
    session = dialog_manager.middleware_data.get('session')
    # admin = await check_admin(session, event_from_user.id)
    # return {'admin': admin}


async def user_panel_text(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    **kwargs
) -> str:
    return {'hello_message': i18n.get('hello-message')}