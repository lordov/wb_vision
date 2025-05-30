from aiogram.enums import ContentType

from aiogram_dialog import Dialog, StartMode,  Window
from aiogram_dialog.widgets.kbd import (
    Row,  Column,  Group, Back, Next,
    Cancel, Button, SwitchTo, Select
)
from aiogram_dialog.widgets.text import Format
from aiogram_dialog.widgets.input import MessageInput

from bot.handlers.states import Employee
from .getters import employee_delete, employee_link, employee_start
from .callback import delete_employee

employee = Dialog(
    Window(
        Format('{employee_text}'),
        Column(
            Next(
                Format('{add_btn}'),
                id='next',
            ),
        ),
        SwitchTo(
            Format('{delete_btn}'),
            id='delete_key',
            state=Employee.delete,
            when='if_employee'
        ),
        Column(
            Cancel(
                Format('{back}'),
                id='back_to_menu',
            )
        ),
        state=Employee.start,
        getter=employee_start
    ),
    Window(
        Format('{add_employee_text}'),
        Back(
            Format('{back}'),
            id='back',
        ),
        state=Employee.link,
        getter=employee_link
    ),
    Window(
        Format('{delete_employee_text}'),
        Select(
            Format("{item[0]}"),  # отображаем имя сотрудника
            id="employee_select",
            item_id_getter=lambda item: item[1],  # берем id сотрудника
            items="employees",  # имя переменной из геттера
            on_click=delete_employee,  # обработчик удаления
        ),
        Back(
            Format('{back}'),
            id='back',
        ),
        getter=employee_delete,
        state=Employee.delete
    )

)
