from aiogram import Bot, Router
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import Message

from aiogram_dialog import DialogManager, ShowMode, StartMode

from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession
from .states import UserPanel, Support
from bot.core.config import settings


router = Router()


@router.message(Command('start'))
async def cmd_start(
    message: Message,
    session: AsyncSession,
    dialog_manager: DialogManager,
):
    await dialog_manager.start(state=UserPanel.start, mode=StartMode.RESET_STACK)


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
            settings.admin_id,
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
            settings.admin_id,
            video=message.video.file_id,
            caption=caption
        )
    elif message.audio:
        await bot.send_audio(
            settings.admin_id,
            audio=message.audio.file_id,
            caption=caption
        )
    elif message.voice:
        await bot.send_voice(
            settings.admin_id,
            voice=message.voice.file_id,
            caption=caption
        )
    elif message.text:
        await bot.send_message(
            settings.admin_id,
            caption  # просто текст с подписью
        )

    await message.answer(i18n.get('support-answer'))
    await state.clear()
