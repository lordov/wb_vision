
from aiogram.types import User
from aiogram.types import User
from aiogram_dialog import DialogManager
from fluentogram import TranslatorRunner
from bot.database.uow import UnitOfWork


async def is_admin(dialog_manager: DialogManager, event_from_user: User, **kwargs):
    session = dialog_manager.middleware_data.get('session')
    # admin = await check_admin(session, event_from_user.id)
    # return {'admin': admin}


async def lk_start(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    **kwargs
) -> dict:
    uow: UnitOfWork = dialog_manager.middleware_data.get('uow')
    user: User = await uow.users.get_by_telegram_id(event_from_user.id)
    return {
        'lk_start': i18n.get('lk-start', id=user.id),
        'lk_settings': i18n.get('lk-settings-btn'),
        'lk_api_key': i18n.get('lk-api-key-btn'),
        'lk_donate': i18n.get('lk-donate-btn'),
    }


async def donate_getter(
        dialog_manager: DialogManager,
        i18n: TranslatorRunner,
        event_from_user: User,
        **kwargs
) -> dict:
    return {
        'donate_text': i18n.get('donate-text'),
        'back': i18n.get('back-btn')
        }
