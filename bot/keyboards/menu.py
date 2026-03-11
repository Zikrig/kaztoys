from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from bot.texts.menu import (
    BTN_LIST_MY_LISTINGS,
    BTN_START_SEARCH,
    BTN_MY_LISTINGS,
    BTN_MY_RESPONSES,
    BTN_OPEN_UNCONFIRMED,
    BTN_MY_SUBSCRIPTION,
    BTN_SUPPORT,
)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_LIST_MY_LISTINGS)],
            [KeyboardButton(text=BTN_START_SEARCH)],
            [KeyboardButton(text=BTN_MY_LISTINGS), KeyboardButton(text=BTN_MY_RESPONSES)],
            [KeyboardButton(text=BTN_OPEN_UNCONFIRMED)],
            [KeyboardButton(text=BTN_MY_SUBSCRIPTION), KeyboardButton(text=BTN_SUPPORT)],
        ],
        resize_keyboard=True,
    )
