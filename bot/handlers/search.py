from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.texts.menu import BTN_BACK_TO_MENU
from bot.texts.search import (
    SEARCH_WHAT,
    SEARCH_AGE,
    SEARCH_DISTRICT,
    BTN_NEXT,
    BTN_OFFER_EXCHANGE,
    BTN_CHANGE_PARAMS,
    NO_MORE_LISTINGS,
    BTN_CONTINUE_SEARCH,
)
from bot.keyboards.menu import main_menu_keyboard
from bot.keyboards.common import back_to_menu_keyboard
from bot.keyboards.report import report_button_row
from bot.keyboards.categories import category_search_keyboard, age_search_keyboard, CATEGORIES, AGES
from bot.keyboards.districts import district_search_keyboard
from bot.services.user import get_user_by_telegram_id
from bot.services.search import (
    save_search_filters,
    get_search_filters,
    get_listing_page,
    get_listing_with_owner,
    update_search_offset,
)
from bot.middlewares.inactivity import MAIN_MENU_STATE

router = Router(name="search")


class SearchStates(StatesGroup):
    wait_category = State()
    wait_age = State()
    wait_district = State()
    showing = State()
    no_results = State()


def _category_label(slug: str) -> str:
    for s, label in CATEGORIES:
        if s == slug:
            return label
    return slug


def _age_label(slug: str) -> str:
    for s, label in AGES:
        if s == slug:
            return label
    return slug


def _district_label(slug: str) -> str:
    from bot.keyboards.districts import DISTRICTS
    for s, label in DISTRICTS:
        if s == slug:
            return label
    return slug


@router.message(F.text == "Начать поиск")
async def start_search(message: Message, state: FSMContext, session, bot: Bot):
    if not message.from_user:
        return
    await state.clear()
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not user:
        await message.answer("Сначала /start.", reply_markup=main_menu_keyboard())
        return
    filters = await get_search_filters(session, user.id)
    if filters and filters.category and filters.age_group and filters.district:
        await state.update_data(
            search_user_id=user.id,
            search_category=filters.category,
            search_age=filters.age_group,
            search_district=filters.district,
            search_offset=filters.offset or 0,
            search_skip_count=0,
            search_hint_shown=False,
        )
        await state.set_state(SearchStates.showing)
        await _send_listing_at_offset(bot=bot, chat_id=message.chat.id, state=state, session=session)
        return
    await state.update_data(search_user_id=user.id, search_skip_count=0, search_hint_shown=False)
    await state.set_state(SearchStates.wait_category)
    await message.answer(SEARCH_WHAT, reply_markup=category_search_keyboard())


@router.callback_query(F.data == "menu:start_search")
async def start_search_callback(callback: CallbackQuery, state: FSMContext, session, bot: Bot):
    if not callback.from_user:
        await callback.answer()
        return
    await state.clear()
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.message.answer("Сначала /start.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    filters = await get_search_filters(session, user.id)
    if filters and filters.category and filters.age_group and filters.district:
        await state.update_data(
            search_user_id=user.id,
            search_category=filters.category,
            search_age=filters.age_group,
            search_district=filters.district,
            search_offset=filters.offset or 0,
            search_skip_count=0,
            search_hint_shown=False,
        )
        await state.set_state(SearchStates.showing)
        await _send_listing_at_offset(bot=bot, chat_id=callback.message.chat.id, state=state, session=session)
        await callback.answer()
        return
    await state.update_data(search_user_id=user.id, search_skip_count=0, search_hint_shown=False)
    await state.set_state(SearchStates.wait_category)
    await callback.message.answer(SEARCH_WHAT, reply_markup=category_search_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("search_cat:"))
async def search_cat_chosen(callback: CallbackQuery, state: FSMContext):
    slug = callback.data.split(":", 1)[1]
    await state.update_data(search_category=slug)
    await state.set_state(SearchStates.wait_age)
    await callback.message.edit_text(SEARCH_AGE)
    await callback.message.answer("Выберите возраст:", reply_markup=age_search_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("search_age:"))
async def search_age_chosen(callback: CallbackQuery, state: FSMContext):
    slug = callback.data.split(":", 1)[1]
    await state.update_data(search_age=slug)
    await state.set_state(SearchStates.wait_district)
    await callback.message.edit_text(SEARCH_DISTRICT)
    await callback.message.answer("Выберите район:", reply_markup=district_search_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("search_district:"))
async def search_district_chosen(callback: CallbackQuery, state: FSMContext, session):
    slug = callback.data.split(":", 1)[1]
    await state.update_data(search_district=slug, search_offset=0, search_skip_count=0, search_hint_shown=False)
    data = await state.get_data()
    user_id = data["search_user_id"]
    await save_search_filters(session, user_id, data["search_category"], data["search_age"], slug)
    await state.set_state(SearchStates.showing)
    await callback.answer()
    await _send_listing_at_offset(bot=callback.bot, chat_id=callback.message.chat.id, state=state, session=session)


async def _send_listing_at_offset(*, bot: Bot, chat_id: int, state: FSMContext, session):
    data = await state.get_data()
    offset = data.get("search_offset", 0)
    category = data.get("search_category") or "all"
    age = data.get("search_age") or "any"
    district = data.get("search_district") or "any"
    user_id = data.get("search_user_id")
    listings = await get_listing_page(session, category, age, district, offset, limit=1, exclude_user_id=user_id)
    if not listings:
        await state.set_state(SearchStates.no_results)
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=BTN_CHANGE_PARAMS, callback_data="search_change_params"),
            InlineKeyboardButton(text=BTN_BACK_TO_MENU, callback_data="search_back_menu"),
        )
        await bot.send_message(chat_id, NO_MORE_LISTINGS, reply_markup=builder.as_markup())
        return
    listing = listings[0]
    row = await get_listing_with_owner(session, listing.id)
    if not row:
        return
    lst, owner = row
    if owner.id == user_id:
        # Safety net: never show the user's own listing in search,
        # even if the repository filter is bypassed somehow.
        await state.update_data(search_offset=offset + 1)
        await _send_listing_at_offset(bot=bot, chat_id=chat_id, state=state, session=session)
        return
    caption = (
        f"{owner.first_name or 'Пользователь'} ({owner.confirmed_deals} подтв. сделок)\n"
        f"Код заявки «{lst.code}» (сравните с кодом на фото)\n"
        f"Категория: {_category_label(lst.category)}, Возраст: {_age_label(lst.age_group)}\n"
        f"Район: {lst.district or 'Любой'}\n\n{lst.description}"
    )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=BTN_OFFER_EXCHANGE, callback_data=f"search_offer:{lst.id}"),
        InlineKeyboardButton(text=BTN_NEXT, callback_data="search_next"),
    )
    builder.row(*report_button_row(listing_id=lst.id))
    builder.row(InlineKeyboardButton(text=BTN_BACK_TO_MENU, callback_data="search_back_menu"))
    builder.row(InlineKeyboardButton(text=BTN_CHANGE_PARAMS, callback_data="search_change_params"))
    await bot.send_photo(
        chat_id,
        photo=lst.photo_file_id or "",
        caption=caption,
        reply_markup=builder.as_markup(),
    )


SEARCH_HINT_TEXT = "Не нашли нужное? Попробуйте изменить параметры поиска."


@router.callback_query(F.data == "search_next")
async def search_next(callback: CallbackQuery, state: FSMContext, session):
    data = await state.get_data()
    skip_count = data.get("search_skip_count", 0) + 1
    hint_shown = data.get("search_hint_shown", False)
    offset = data.get("search_offset", 0) + 1
    await state.update_data(search_offset=offset, search_skip_count=skip_count)
    user_id = data.get("search_user_id")
    if user_id is not None:
        await update_search_offset(session, user_id, offset)
    if skip_count >= 7 and not hint_shown:
        await callback.message.delete()
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=BTN_CHANGE_PARAMS, callback_data="search_change_params"),
            InlineKeyboardButton(text=BTN_CONTINUE_SEARCH, callback_data="search_continue_after_hint"),
        )
        await callback.bot.send_message(
            callback.message.chat.id,
            SEARCH_HINT_TEXT,
            reply_markup=builder.as_markup(),
        )
        await state.update_data(search_hint_shown=True)
        await callback.answer()
        return
    await callback.message.delete()
    await _send_listing_at_offset(bot=callback.bot, chat_id=callback.message.chat.id, state=state, session=session)
    await callback.answer()


@router.callback_query(F.data == "search_continue_after_hint")
async def search_continue_after_hint(callback: CallbackQuery, state: FSMContext, session):
    await callback.message.delete()
    await _send_listing_at_offset(bot=callback.bot, chat_id=callback.message.chat.id, state=state, session=session)
    await callback.answer()


@router.callback_query(F.data == "search_change_params")
async def search_change_params(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchStates.wait_category)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(SEARCH_WHAT, reply_markup=category_search_keyboard())
    await callback.answer()


@router.callback_query(F.data == "search_back_menu")
async def search_back_menu(callback: CallbackQuery, state: FSMContext):
    from bot.keyboards.menu import main_menu_keyboard
    await state.clear()
    await state.set_state(MAIN_MENU_STATE)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "search_continue_after_response")
async def search_continue_after_response(callback: CallbackQuery, state: FSMContext, session):
    """After sending response from search flow: show next listing."""
    data = await state.get_data()
    offset = data.get("search_offset", 0) + 1
    await state.update_data(search_offset=offset)
    user_id = data.get("search_user_id")
    if user_id is not None:
        await update_search_offset(session, user_id, offset)
    await state.set_state(SearchStates.showing)
    await callback.message.delete()
    await _send_listing_at_offset(bot=callback.bot, chat_id=callback.message.chat.id, state=state, session=session)
    await callback.answer()

