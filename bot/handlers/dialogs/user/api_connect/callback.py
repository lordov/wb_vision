from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram.types import Message
from aiogram_dialog.widgets.kbd import Button

from fluentogram import TranslatorRunner
from cryptography.fernet import Fernet

from bot.database.uow import UnitOfWork
from bot.services.api_key import ApiKeyService
from bot.services.subscription import SubscriptionService
from bot.core.logging import app_logger


async def api_key_input(
    message: Message,
    button: Button,
    dialog_manager: DialogManager,
):
    uow: UnitOfWork = dialog_manager.middleware_data["uow"]
    i18n: TranslatorRunner = dialog_manager.middleware_data["i18n"]
    fernet: Fernet = dialog_manager.middleware_data["fernet"]
    user = message.from_user
    raw_key = message.text.strip()

    try:
        # Валидация ключа
        if not validate_wb_api_key_format(raw_key):
            await message.answer(i18n.get("api-key-invalid"))
            return

        # Проверка доступности пробного периода
        subscription_service = SubscriptionService(uow)
        can_use_trial = await subscription_service.check_trial(user.id)

        if not can_use_trial:
            await message.answer(i18n.get("api-key-trial-expired"))
            return

        # Работа с API ключами
        api_key_service = ApiKeyService(repo=uow.api_keys, fernet=fernet)
        await api_key_service.set_key(user.id, "wb_stats", raw_key)
        await uow.commit()

        app_logger.info("API Key added", user_id=user.id)
        await message.answer(i18n.get("api-key-success"))
        await dialog_manager.done()

    except Exception as e:
        app_logger.exception("API Key save failed",
                             error=str(e), user_id=user.id)
        await message.answer(i18n.get("unexpected-error"))


def validate_wb_api_key_format(key: str) -> bool:
    return len(key) > 30
