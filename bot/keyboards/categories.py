from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Category slugs for DB and callbacks (v4)
CATEGORY_SCOOTERS = "scooters_bikes"
CATEGORY_BABIES = "for_babies"
CATEGORY_DOLLS = "dolls_figures"
CATEGORY_CARS = "cars_guns"
CATEGORY_OTHER = "other"

CATEGORIES = [
    (CATEGORY_SCOOTERS, "Самокаты, велики и транспорт"),
    (CATEGORY_BABIES, "Для малышей (0–2 года)"),
    (CATEGORY_DOLLS, "Куклы, фигурки и наборы"),
    (CATEGORY_CARS, "Машинки и стрелялки"),
    (CATEGORY_OTHER, "Другое (домики, горки и т.д.)"),
]

# Age groups
AGE_0_2 = "0_2"
AGE_3_5 = "3_5"
AGE_6_8 = "6_8"
AGE_9_12 = "9_12"
AGE_ANY = "any"

AGES = [
    (AGE_0_2, "0–2 года"),
    (AGE_3_5, "3–5 лет"),
    (AGE_6_8, "6–8 лет"),
    (AGE_9_12, "9–12 лет"),
    (AGE_ANY, "Любой возраст"),
]

ALL_CATEGORIES_SLUG = "all"


def category_keyboard(prefix: str = "cat") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slug, label in CATEGORIES:
        builder.row(InlineKeyboardButton(text=label, callback_data=f"{prefix}:{slug}"))
    return builder.as_markup()


def age_keyboard(prefix: str = "age") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slug, label in AGES:
        builder.row(InlineKeyboardButton(text=label, callback_data=f"{prefix}:{slug}"))
    return builder.as_markup()


def category_search_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Все категории", callback_data="search_cat:all"))
    for slug, label in CATEGORIES:
        builder.row(InlineKeyboardButton(text=label, callback_data=f"search_cat:{slug}"))
    return builder.as_markup()


def age_search_keyboard() -> InlineKeyboardMarkup:
    return age_keyboard(prefix="search_age")
