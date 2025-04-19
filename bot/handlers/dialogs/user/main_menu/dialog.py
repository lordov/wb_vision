from aiogram.enums import ContentType

from aiogram_dialog import Dialog,  Window
from aiogram_dialog.widgets.kbd import (
    Row,  Column,  Group, Back, Next,
    Cancel, Button, SwitchTo, Start,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput

from bot.handlers.states import UserPanel
from .getters import user_panel_text


user_panel = Dialog(
    Window(
        Format('{hello_message}'),
        getter=user_panel_text,
        state=UserPanel.start
    ),
)
