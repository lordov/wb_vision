from aiogram.fsm.state import State, StatesGroup


class UserPanel(StatesGroup):
    start = State()

class Support(StatesGroup):
    question = State()
