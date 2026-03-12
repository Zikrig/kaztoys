from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.report import REPORT_REASON_CONTENT, REPORT_REASON_HIDE, REPORT_REASON_RULES


def report_button_row(*, listing_id: int) -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text="Жалоба", callback_data=f"rep:start:{listing_id}")]


def report_reason_keyboard(listing_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Неприемлемый контент",
            callback_data=f"rep:rsn:{listing_id}:{REPORT_REASON_CONTENT}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Не соответствует правилам",
            callback_data=f"rep:rsn:{listing_id}:{REPORT_REASON_RULES}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Просто скрыть автора",
            callback_data=f"rep:rsn:{listing_id}:{REPORT_REASON_HIDE}",
        )
    )
    return builder.as_markup()
