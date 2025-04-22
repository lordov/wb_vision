from aiogram.enums import ContentType

from aiogram_dialog import Dialog,  Window
from aiogram_dialog.widgets.kbd import (
    Row,  Column,  Group, Back, Next,
    Cancel, Button, SwitchTo, Start,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput

from bot.handlers.states import UserPanel
from .getters import lk_start


user_panel = Dialog(
    Window(
        Format('{lk_start}'),
        getter=lk_start,
        state=UserPanel.start
    ),
)
