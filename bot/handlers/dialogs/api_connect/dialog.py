from aiogram.enums import ContentType

from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import (
    Column,  Group, Back, Next,
    Cancel, Button
)
from aiogram_dialog.widgets.text import Format
from aiogram_dialog.widgets.input import MessageInput

from bot.handlers.states import ApiPanel
from .getters import api_start, key_input
from .callback import api_key_input, delete_api_key


api_connect = Dialog(
    Window(
        Format('{api_key_text}'),
        Group(
            Column(
                Next(
                    Format('{api_key_btn}'),
                    id='next',
                    when='active'
                ),
                Button(
                    Format('{api_key_btn}'),
                    id='delete_key',
                    on_click=delete_api_key,
                    when='inactive'
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
