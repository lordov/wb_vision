from aiogram import Bot, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message, BotCommand, CallbackQuery

from aiogram_dialog import DialogManager, StartMode

from fluentogram import TranslatorRunner

from bot.core.dependency.container import DependencyContainer
from bot.services.users import UserService
from .kbd.keyboards import lk_main_button
from .states import UserPanel, Support
from bot.core.config import settings
from broker import start_load_stocks, start_notif_pipline


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


@router.message(CommandStart(deep_link=True))
async def start_with_deeplink(
    message: Message,
    i18n: TranslatorRunner,
    command: CommandObject,
    container: DependencyContainer
):
    bot = message.bot
    user_service = await container.get(UserService)
    username = message.from_user.username
    await user_service.add_user(
        telegram_id=message.from_user.id,
        username=username if username else None,
        locale=message.from_user.language_code
    )
    if command.args and command.args.startswith("addstaff_"):

        parts = command.args.split("_")
        if len(parts) != 3:
            return

        owner_id, token = int(parts[1]), parts[2]
        inviate = await user_service.check_invite(owner_id, token)
        owner = await user_service.get_by_user_id(owner_id)

        if owner.telegram_id == message.from_user.id:
            await message.answer(i18n.get("self-error"))
            return

        if inviate is None:
            await message.answer(i18n.get("wrong-link"))
            return

        # Проверка: не был ли уже добавлен сотрудник
        if await user_service.check_user_as_employee(message.from_user.id):
            await message.answer(i18n.get("employee-exist"))
            return

        # Добавление сотрудника
        await user_service.add_employee(owner_id, message.from_user.id, username, token)
        await message.answer(i18n.get("employee-added"))
        await bot.send_message(owner.telegram_id, i18n.get("notif-owner", user_id=message.from_user.id))

    else:
        await message.answer(i18n.get('hello-message'))


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    i18n: TranslatorRunner,
    container: DependencyContainer,
):
    user_service = await container.get(UserService)
    await user_service.add_user(
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
    container: DependencyContainer,
):
    await start_notif_pipline(container=container)


@router.message(Command('support'))
async def support_message(message: Message, i18n: TranslatorRunner, state: FSMContext):
    keyboard = lk_main_button(i18n)
    await state.set_state(Support.question)
    await message.answer(i18n.get('support-message'), reply_markup=keyboard)


@router.callback_query(F.data == 'lk_main')
async def lk_main(callback: CallbackQuery, dialog_manager: DialogManager):
    await dialog_manager.start(UserPanel.start, mode=StartMode.RESET_STACK)


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
        message=message.text or message.caption or "📎 Мультимедиа сообщение"
    )

    # Обрабоотку медиа груп необходимо предоставить
    if message.photo:
        await bot.send_photo(
            settings.bot.admin_id,
            photo=message.photo[-1].file_id,
            caption=caption
        )
    elif message.document:
        await bot.send_document(
            settings.bot.admin_id,
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
