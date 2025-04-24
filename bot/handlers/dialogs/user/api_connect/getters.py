from aiogram.types import User
from aiogram_dialog import DialogManager
from fluentogram import TranslatorRunner


async def api_start(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    **kwargs
) -> dict:
    return {
        'api_key_text': i18n.get('api-key-text'),
        'api_key_btn': i18n.get('api-key-btn'),
        'back': i18n.get('back-btn')
    }

async def key_input(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    **kwargs
) -> dict:
    return {
        'api_key_input': i18n.get('api-key-input'),
        'back': i18n.get('back-btn')
    }
