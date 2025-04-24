from aiogram.enums import ContentType

from aiogram_dialog import Dialog, StartMode,  Window
from aiogram_dialog.widgets.kbd import (
    Row,  Column,  Group, Back, Next,
    Cancel, Button, SwitchTo, Start,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput

from bot.handlers.states import ApiPanel
from .getters import api_start, key_input
from callback import api_key_input


api_connect = Dialog(
    Window(
        Format('{api_key_text}'),
        Group(
            Column(
                Next(
                    Format('{api_key_btn}'),
                    id='next',
                )
            ),
            Column(
                Cancel(
                    Format('{back}'),
                    id='back_to_menu',
                )
            )
        ),
        state=ApiPanel.start,
        getter=api_start
    ),
    Window(
        Format('{api_key_input}'),
        MessageInput(
            func=api_key_input,
            content_types=ContentType.TEXT,
        ),
        Back(
            Format('{back}'),
            id='back_to_menu',
        ),
        state=ApiPanel.input,
        getter=key_input
    )
)
