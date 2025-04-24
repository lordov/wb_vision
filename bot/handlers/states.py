from aiogram.fsm.state import State, StatesGroup


class UserPanel(StatesGroup):
    start = State()
    settings = State()
    donate = State()
    stats = State()
    subscription = State()
    employee = State()

class Support(StatesGroup):
    question = State()

class ApiPanel(StatesGroup):
    start = State()
    input = State()