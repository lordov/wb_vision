from aiogram.fsm.state import State, StatesGroup


class UserPanel(StatesGroup):
    start = State()
    settings = State()
    api_key = State()
    stats = State()
    subscription = State()
    employee = State()

class Support(StatesGroup):
    question = State()
