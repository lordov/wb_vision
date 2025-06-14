from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import (
    Column, Back, Next,
    Cancel, SwitchTo, Select
)
from aiogram_dialog.widgets.text import Format

from bot.handlers.states import Employee
from .getters import employee_delete, employee_link, employee_start
from .callback import delete_employee_clbc

employee = Dialog(
    Window(
        Format('{employee_text}'),
        Column(
            Next(
                Format('{add_btn}'),
                id='next',
                when='can_add_employee'
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
            Format("Удалить {item[0]}"),
            id="employee_select",
            item_id_getter=lambda item: item[1],
            items="employees",
            on_click=delete_employee_clbc,
        ),
        SwitchTo(
            Format('{back}'),
            id='back',
            state=Employee.start
        ),
        getter=employee_delete,
        state=Employee.delete
    )

)
