from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Districts of Astana (Nur-Sultan) for search filter
# Can be extended or loaded from DB later
DISTRICTS = [
    ("almaty", "Алматы"),
    ("yesil", "Есіл"),
    ("saryarka", "Сарыарқа"),
    ("baykonur", "Байқоңыр"),
    ("any", "Любой район"),
]
ANY_DISTRICT_SLUG = "any"


def district_keyboard(prefix: str = "district") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slug, label in DISTRICTS:
        builder.row(
            InlineKeyboardButton(text=label, callback_data=f"{prefix}:{slug}")
        )
    return builder.as_markup()


def district_search_keyboard() -> InlineKeyboardMarkup:
    return district_keyboard(prefix="search_district")
