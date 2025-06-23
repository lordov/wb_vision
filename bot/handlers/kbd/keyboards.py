from aiogram import types
from fluentogram import TranslatorRunner


def lk_main_button(i18n: TranslatorRunner):
    buttons = [
        [
            types.InlineKeyboardButton(text=i18n.get(
                'lk-main-btn'), callback_data='lk_main')
        ]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
