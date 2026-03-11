from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from bot.texts.menu import BTN_BACK_TO_MENU, BTN_CANCEL


def back_to_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_BACK_TO_MENU)]],
        resize_keyboard=True,
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )
