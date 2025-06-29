from aiogram_dialog import DialogManager
from aiogram.types import Message
from aiogram_dialog.widgets.kbd import Button

from fluentogram import TranslatorRunner

from bot.database.uow import UnitOfWork
from bot.core.dependency.container import DependencyContainer
from bot.core.logging import app_logger
from bot.handlers.states import ApiPanel
from broker import pre_load_info


async def api_key_input(
    message: Message,
    button: Button,
    dialog_manager: DialogManager,
):
    uow: UnitOfWork = dialog_manager.middleware_data["uow"]
    i18n: TranslatorRunner = dialog_manager.middleware_data["i18n"]
    container: DependencyContainer = dialog_manager.middleware_data["container"]
    user = message.from_user
    raw_key = message.text.strip()
    # Работа с API ключами
    subscription_service = container.get_subscription_service(uow)
    api_key_service = container.get_api_key_service(uow)

    try:
        if not await api_key_service.validate_wb_api_key(raw_key):
            await message.answer(i18n.get("api-key-invalid"))
            return

        if not await api_key_service.check_request_to_wb(raw_key):
            await message.answer(i18n.get("api-key-invalid-request"))
            return

        status = await api_key_service.set_api_key_with_subscription_check(
            telegram_id=user.id,
            title="wb_stats",
            raw_key=raw_key,
            subscription_service=subscription_service,
        )

        if status == "active":
            await message.answer(i18n.get("api-key-success"))
            await dialog_manager.switch_to(ApiPanel.start)
            app_logger.info("API Key saved successfully", user_id=user.id)
        elif status == "trial_activated":
            await message.answer(i18n.get("subscribe-trial-activeated"))
            await dialog_manager.switch_to(ApiPanel.start)
            app_logger.info("Trial activated", user_id=user.id)
        else:
            await message.answer(
                i18n.get("subscribe-to-activate-key")
            )
            await dialog_manager.switch_to(ApiPanel.start)

        await message.answer(i18n.get("api-key-pre-load"))
        await pre_load_info.kiq(telegram_id=user.id)

    except Exception as e:
        app_logger.exception("API Key save failed",
                             error=str(e), user_id=user.id)
        await message.answer('Непредвиденная ошибка')


async def delete_api_key(
    message: Message,
    button: Button,
    dialog_manager: DialogManager,
):
    uow: UnitOfWork = dialog_manager.middleware_data["uow"]
    i18n: TranslatorRunner = dialog_manager.middleware_data["i18n"]
    container: DependencyContainer = dialog_manager.middleware_data["container"]
    user = message.from_user
    api_key_service = container.get_api_key_service(uow)
    try:
        await api_key_service.delete_key(user.id)
        await message.answer(i18n.get("api-key-deleted"))
        await dialog_manager.switch_to(ApiPanel.start)
        app_logger.info("API Key deleted", user_id=user.id)
    except Exception as e:
        app_logger.exception("API Key delete failed",
                             error=str(e), user_id=user.id)
        await message.answer('Непредвиденная ошибка')
