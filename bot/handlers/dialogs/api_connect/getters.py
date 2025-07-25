from aiogram.types import User
from aiogram_dialog import DialogManager
from fluentogram import TranslatorRunner
from bot.core.dependency.container import DependencyContainer
from bot.database.uow import UnitOfWork


async def api_start(
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    event_from_user: User,
    container: DependencyContainer,
    uow: UnitOfWork,
    **kwargs
) -> dict:
    api_key_service = container.get_api_key_service(uow)
    key = await api_key_service.get_user_key(event_from_user.id)

    has_key = key is not None
    status = "delete" if has_key else "set"

    return {
        'api_key_text': i18n.get('api-key-text', has_key=str(has_key).lower()),
        'api_key_btn': i18n.get('api-key-btn', status=status),
        'back': i18n.get('back-btn'),
        'active': not has_key,
        'inactive': has_key,
        'delete_api_key_btn': i18n.get('delete-api-key-btn', status=status),
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
