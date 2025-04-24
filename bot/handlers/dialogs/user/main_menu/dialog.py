from aiogram.enums import ContentType

from aiogram_dialog import Dialog, StartMode,  Window
from aiogram_dialog.widgets.kbd import (
    Row,  Column,  Group, Back, Next,
    Cancel, Button, SwitchTo, Start,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput

from bot.handlers.states import UserPanel, ApiPanel
from .getters import donate_getter, lk_start


user_panel = Dialog(
    Window(
        Format('{lk_start}'),
        Group(
            Column(
                Start(
                    Format('{lk_api_key}'),
                    id='lk_api_key',
                    state=ApiPanel.start,
                    mode=StartMode.NORMAL
                )
            ),
            Column(
                Start(
                    Format('{lk_settings}'),
                    id='lk_settings',
                    state=UserPanel.settings,
                    mode=StartMode.NORMAL
                )
            ),
            Column(
                SwitchTo(
                    Format('{lk_donate}'),
                    id='lk_donate',
                    state=UserPanel.donate,
                )
            )
        ),
        getter=lk_start,
        state=UserPanel.start
    ),
    Window(
        Format('{donate_text}'),
        Column(
            Back(
                Format('{back}'),
                id='back',
            ),
        ),
        getter=donate_getter,
        state=UserPanel.donate
    )
)
