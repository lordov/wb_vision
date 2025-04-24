from aiogram.fsm.state import State, StatesGroup


class UserPanel(StatesGroup):
    start = State()
    api_key = State()
    settings = State()
    donate = State()
    stats = State()
    subscription = State()
    employee = State()

class Support(StatesGroup):
    question = State()
