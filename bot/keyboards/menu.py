from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.texts.menu import (
    BTN_LIST_MY_LISTINGS,
    BTN_START_SEARCH,
    BTN_MY_LISTINGS,
    BTN_MY_RESPONSES,
    BTN_OPEN_UNCONFIRMED,
    BTN_MY_SUBSCRIPTION,
    BTN_SUPPORT,
    BTN_REFERRAL,
)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=BTN_START_SEARCH, callback_data="menu:start_search"))
    builder.row(InlineKeyboardButton(text=BTN_LIST_MY_LISTINGS, callback_data="menu:new_listing"))
    builder.row(
        InlineKeyboardButton(text=BTN_MY_LISTINGS, callback_data="menu:my_listings"),
        InlineKeyboardButton(text=BTN_MY_RESPONSES, callback_data="menu:my_responses"),
    )
    builder.row(InlineKeyboardButton(text=BTN_OPEN_UNCONFIRMED, callback_data="menu:open_unconfirmed"))
    builder.row(
        InlineKeyboardButton(text=BTN_MY_SUBSCRIPTION, callback_data="menu:subscription"),
        InlineKeyboardButton(text=BTN_SUPPORT, callback_data="menu:support"),
    )
    builder.row(InlineKeyboardButton(text=BTN_REFERRAL, callback_data="menu:referral"))
    return builder.as_markup()
