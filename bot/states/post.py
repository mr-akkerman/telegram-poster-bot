from aiogram.fsm.state import State, StatesGroup


class CreatePost(StatesGroup):
    waiting_for_text = State()
    waiting_for_buttons = State()
    preview = State()
    select_channel = State()
