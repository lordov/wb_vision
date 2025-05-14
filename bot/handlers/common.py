from aiogram import Bot, Router
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, BotCommand

from aiogram_dialog import DialogManager, StartMode

from fluentogram import TranslatorRunner

from bot.core.dependency.container import DependencyContainer
from bot.database.uow import UnitOfWork
from bot.services.api_key import ApiKeyService
from bot.services.notifications import NotificationService
from bot.services.wb_service import WBService
from .states import UserPanel, Support
from bot.core.config import settings


router = Router()


@router.startup()
async def on_startup(bot: Bot):
    # Список команд, которые будут отображаться пользователю
    commands = [
        BotCommand(command="/support", description="🧑‍💻 Поддержка"),
        BotCommand(command="/lk", description="👤 Личный кабинет"),
        # Можно добавить другие команды
    ]
    await bot.delete_my_commands()
    # Псмотреть манул по командам для разных языков
    # Устанавливаем команды для бота
    await bot.set_my_commands(commands)


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    uow: UnitOfWork,
    i18n: TranslatorRunner,
):
    await uow.users.get_or_create(
        message.from_user.id,
        message.from_user.username,
        message.from_user.language_code
    )
    await message.answer(i18n.get('hello-message'))


@router.message(Command('lk'))
async def lk_start(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(UserPanel.start, mode=StartMode.RESET_STACK)


@router.message(Command("task"))
async def task(
    message: Message,
    i18n: TranslatorRunner,
    container: DependencyContainer,
):
    async def notify_user_about_orders(
        user_id: int,
        telegram_id: int,
        orders: list[dict],
        container: DependencyContainer
    ):
        service = await container.get(NotificationService)
        await service.send_message(user_id=user_id, telegram_id=telegram_id, orders=orders)

    async def fetch_and_save_orders_for_key(
        user_id: int,
        telegram_id: int,
        key_encrypted: str,
        container: DependencyContainer
    ):
        async with await container.create_uow():
            service = await container.get(WBService)
            new_orders = await service.fetch_and_save_orders(api_key=key_encrypted, user_id=user_id)

            if new_orders:
                await notify_user_about_orders(user_id, telegram_id, new_orders, container=container)

    service = await container.get(ApiKeyService)
    async with await container.create_uow():
        api_keys = await service.get_all_decrypted_keys()
        for key in api_keys:
            await fetch_and_save_orders_for_key(
                user_id=key.user_id,
                key_encrypted=key.key_encrypted,
                telegram_id=key.telegram_id,
                container=container
            )
        print(f'{key.key_encrypted} отправлен в задачу')


@router.message(Command('support'))
async def support_message(message: Message, i18n: TranslatorRunner, state: FSMContext):
    await state.set_state(Support.question)
    await message.answer(i18n.get('support-message'))


@router.message(Support.question)
async def question_from_user(
    message: Message,
    i18n: TranslatorRunner,
    state: FSMContext,
    bot: Bot
):
    user = message.from_user
    user_label = f"@{user.username}" if user.username else f"id: {user.id}"

    # Если нет ни текста, ни медиа — ошибка
    if not any([message.text, message.photo, message.document, message.video, message.audio, message.voice]):
        await message.answer(i18n.get('support-invalid-question'))
        return

    # Подпись (если можно прикрепить)
    caption = i18n.get(
        'support-from-user',
        user_id=user_label,
        message=message.text or "📎 Мультимедиа сообщение"
    )

    # Обрабоотку медиа груп необходимо предоставить
    if message.photo:
        await bot.send_photo(
            settings.bot.admin_id,
            photo=message.photo[-1].file_id,  # самое большое
            caption=caption
        )
    elif message.document:
        await bot.send_document(
            settings.admin_id,
            document=message.document.file_id,
            caption=caption
        )
    elif message.video:
        await bot.send_video(
            settings.bot.admin_id,
            video=message.video.file_id,
            caption=caption
        )
    elif message.audio:
        await bot.send_audio(
            settings.bot.admin_id,
            audio=message.audio.file_id,
            caption=caption
        )
    elif message.voice:
        await bot.send_voice(
            settings.bot.admin_id,
            voice=message.voice.file_id,
            caption=caption
        )
    elif message.text:
        await bot.send_message(
            settings.bot.admin_id,
            caption  # просто текст с подписью
        )

    await message.answer(i18n.get('support-answer'))
    await state.clear()
