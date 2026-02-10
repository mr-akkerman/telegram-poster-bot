from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Button labels — used both in keyboards and in handler filters
BTN_CREATE_POST = "\u270d\ufe0f \u0421\u043e\u0437\u0434\u0430\u0442\u044c \u043f\u043e\u0441\u0442"
BTN_MY_CHANNELS = "\U0001f4e2 \u041c\u043e\u0438 \u043a\u0430\u043d\u0430\u043b\u044b"
BTN_MY_POSTS = "\U0001f4cb \u041c\u043e\u0438 \u043f\u043e\u0441\u0442\u044b"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CREATE_POST)],
            [KeyboardButton(text=BTN_MY_CHANNELS), KeyboardButton(text=BTN_MY_POSTS)],
        ],
        resize_keyboard=True,
    )
