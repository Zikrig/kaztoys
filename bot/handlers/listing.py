from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.texts.menu import BTN_BACK_TO_MENU
from bot.texts.listing import (
    CODE_PROMPT,
    CHOOSE_CATEGORY,
    CHOOSE_AGE,
    DESCRIPTION_PROMPT,
    CONFIRM_LISTING,
    LISTING_SENT,
    BTN_CONFIRM_SEND,
    BTN_EDIT,
)
from bot.texts.errors import NOT_A_PHOTO, NOT_TEXT
from bot.keyboards.common import back_to_menu_keyboard
from bot.keyboards.menu import main_menu_keyboard
from bot.keyboards.report import report_button_row
from bot.keyboards.categories import (
    category_keyboard,
    age_keyboard,
    CATEGORIES,
    AGES,
    CATEGORY_BABIES,
    AGE_0_2,
)
from bot.services.user import get_user_by_telegram_id
from bot.services.listing import (
    generate_unique_code,
    create_listing,
    get_open_listings_by_user,
    get_listing_by_id,
    close_listing,
)
from bot.services.subscription import has_active_subscription, create_subscription
from bot.services.report import can_view_listing
from bot.middlewares.inactivity import MAIN_MENU_STATE


async def _broadcast_new_listing(session, bot, listing, author_user_id: int):
    """Notify users with active subscription about new listing (excluding author)."""
    from sqlalchemy import select
    from bot.models.user import User
    from bot.models.subscription import Subscription
    from datetime import datetime, timezone
    result = await session.execute(
        select(User.id, User.telegram_id).join(Subscription, User.id == Subscription.user_id).where(
            Subscription.expires_at > datetime.now(timezone.utc),
            User.id != author_user_id,
            User.is_blocked.is_(False),
        ).distinct()
    )
    recipients = result.all()
    from bot.models.user import User as U
    author = await session.get(U, author_user_id)
    name = author.first_name or "Пользователь" if author else "Пользователь"
    deals = author.confirmed_deals if author else 0
    caption = (
        f"НОВАЯ ЗАЯВКА! {name} ({deals} подтверждённых сделок)\n"
        f"Код №{listing.code} (сравните с кодом на фото)\n\n{listing.description}"
    )
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Отправить предложение", callback_data=f"search_offer:{listing.id}"))
    builder.row(*report_button_row(listing_id=listing.id))
    for recipient_user_id, tid in recipients:
        if not await can_view_listing(session, viewer_user_id=recipient_user_id, author_user_id=author_user_id):
            continue
        try:
            await bot.send_photo(tid, photo=listing.photo_file_id or "", caption=caption, reply_markup=builder.as_markup())
        except Exception:
            pass


router = Router(name="listing")


class ListingCreateStates(StatesGroup):
    wait_photo = State()
    wait_category = State()
    wait_age = State()
    wait_description = State()
    confirm = State()


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


@router.message(F.text == "Выставить свою игрушку")
async def start_listing_create(message: Message, state: FSMContext, session):
    if not message.from_user:
        return
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not user:
        await state.clear()
        await state.set_state(MAIN_MENU_STATE)
        await message.answer("Главное меню.", reply_markup=main_menu_keyboard())
        return
    active = await has_active_subscription(session, user.id)
    if not active:
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="Купить доступ на 2 недели", callback_data="listing_buy_sub"))
        builder.row(InlineKeyboardButton(text="В главное меню", callback_data="listing_back_menu"))
        await message.answer(
            "Для создания заявки нужна подписка. Подключить доступ на 2 недели?",
            reply_markup=builder.as_markup(),
        )
        return
    code = await generate_unique_code(session)
    await state.update_data(listing_code=code, listing_user_id=user.id)
    await state.set_state(ListingCreateStates.wait_photo)
    await message.answer(CODE_PROMPT.format(code=code), reply_markup=back_to_menu_keyboard())


@router.callback_query(F.data == "menu:new_listing")
async def start_listing_create_callback(callback: CallbackQuery, state: FSMContext, session):
    if not callback.from_user:
        await callback.answer()
        return
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await state.clear()
        await state.set_state(MAIN_MENU_STATE)
        await callback.message.answer("Главное меню.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    active = await has_active_subscription(session, user.id)
    if not active:
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="Купить доступ на 2 недели", callback_data="listing_buy_sub"))
        builder.row(InlineKeyboardButton(text="В главное меню", callback_data="menu:main"))
        await callback.message.answer(
            "Для создания заявки нужна подписка. Подключить доступ на 2 недели?",
            reply_markup=builder.as_markup(),
        )
        await callback.answer()
        return
    code = await generate_unique_code(session)
    await state.update_data(listing_code=code, listing_user_id=user.id)
    await state.set_state(ListingCreateStates.wait_photo)
    await callback.message.answer(CODE_PROMPT.format(code=code), reply_markup=back_to_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "listing_buy_sub")
async def listing_buy_sub(callback: CallbackQuery, state: FSMContext, session):
    if not callback.from_user:
        await callback.answer()
        return
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.answer("Сначала нажмите /start.")
        return
    await create_subscription(session, user.id, days=14)
    code = await generate_unique_code(session)
    await state.update_data(listing_code=code, listing_user_id=user.id)
    await state.set_state(ListingCreateStates.wait_photo)
    await callback.answer("Подписка подключена.")
    await callback.message.answer(CODE_PROMPT.format(code=code), reply_markup=back_to_menu_keyboard())


@router.callback_query(F.data == "listing_back_menu")
async def listing_back_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(MAIN_MENU_STATE)
    await callback.answer()
    await callback.message.answer("Главное меню.", reply_markup=main_menu_keyboard())


@router.message(ListingCreateStates.wait_photo, F.photo)
async def listing_photo_received(message: Message, state: FSMContext, session):
    photo = message.photo[-1]
    file_id = photo.file_id
    data = await state.get_data()
    code = data.get("listing_code")
    user_id = data.get("listing_user_id")
    await state.update_data(listing_photo_file_id=file_id)
    await state.set_state(ListingCreateStates.wait_category)
    await message.answer(CHOOSE_CATEGORY, reply_markup=category_keyboard(prefix="listing_cat"))


@router.message(ListingCreateStates.wait_photo, F.text)
async def listing_photo_not_photo(message: Message, state: FSMContext):
    if message.text == BTN_BACK_TO_MENU:
        await state.clear()
        await state.set_state(MAIN_MENU_STATE)
        await message.answer("Главное меню.", reply_markup=main_menu_keyboard())
        return
    await message.answer(NOT_A_PHOTO)


@router.callback_query(F.data.startswith("listing_cat:"))
async def listing_category_chosen(callback: CallbackQuery, state: FSMContext):
    slug = callback.data.split(":", 1)[1]
    await state.update_data(listing_category=slug)
    # If category is "для малышей", age is fixed to 0–2 years and we skip asking
    if slug == CATEGORY_BABIES:
        await state.update_data(listing_age=AGE_0_2)
        await state.set_state(ListingCreateStates.wait_description)
        await callback.message.edit_text(DESCRIPTION_PROMPT)
        await callback.answer()
        return
    await state.set_state(ListingCreateStates.wait_age)
    await callback.message.edit_text(CHOOSE_AGE)
    await callback.message.answer("Выберите возраст:", reply_markup=age_keyboard(prefix="listing_age"))
    await callback.answer()


@router.message(ListingCreateStates.wait_category)
async def listing_category_ignore(message: Message):
    await message.answer("Выберите категорию кнопкой выше.")


@router.callback_query(F.data.startswith("listing_age:"))
async def listing_age_chosen(callback: CallbackQuery, state: FSMContext):
    slug = callback.data.split(":", 1)[1]
    await state.update_data(listing_age=slug)
    await state.set_state(ListingCreateStates.wait_description)
    await callback.message.edit_text(DESCRIPTION_PROMPT)
    await callback.answer()


@router.message(ListingCreateStates.wait_age)
async def listing_age_ignore(message: Message):
    await message.answer("Выберите возраст кнопкой.")


@router.message(ListingCreateStates.wait_description, F.text)
async def listing_description_received(message: Message, state: FSMContext, session):
    if message.text == BTN_BACK_TO_MENU:
        await state.clear()
        await state.set_state(MAIN_MENU_STATE)
        await message.answer("Главное меню.", reply_markup=main_menu_keyboard())
        return
    description = message.text
    await state.update_data(listing_description=description)
    data = await state.get_data()
    code = data["listing_code"]
    photo_file_id = data["listing_photo_file_id"]
    category = data["listing_category"]
    age = data["listing_age"]
    user_id = data["listing_user_id"]
    cat_label = _category_label(category)
    age_label = _age_label(age)
    preview = (
        f"Код заявки: {code}\nКатегория: {cat_label}\nВозраст: {age_label}\nОписание: {description}\n\n{CONFIRM_LISTING}"
    )
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=BTN_CONFIRM_SEND, callback_data="listing_confirm:send"),
        InlineKeyboardButton(text=BTN_EDIT, callback_data="listing_confirm:edit"),
    )
    builder.row(InlineKeyboardButton(text=BTN_BACK_TO_MENU, callback_data="menu:main"))
    await state.set_state(ListingCreateStates.confirm)
    await message.answer_photo(photo=photo_file_id, caption=preview, reply_markup=builder.as_markup())


@router.message(ListingCreateStates.wait_description)
async def listing_description_not_text(message: Message):
    await message.answer(NOT_TEXT)


@router.callback_query(ListingCreateStates.confirm, F.data == "listing_confirm:send")
async def listing_confirm_send(callback: CallbackQuery, state: FSMContext, session, bot):
    data = await state.get_data()
    user_id = data["listing_user_id"]
    code = data["listing_code"]
    photo_file_id = data["listing_photo_file_id"]
    category = data["listing_category"]
    age = data["listing_age"]
    description = data["listing_description"]
    listing = await create_listing(
        session,
        user_id=user_id,
        code=code,
        photo_file_id=photo_file_id,
        category=category,
        age_group=age,
        district=None,
        description=description,
    )
    await state.clear()
    await state.set_state(MAIN_MENU_STATE)
    await callback.message.answer(LISTING_SENT, reply_markup=main_menu_keyboard())
    await _broadcast_new_listing(session, bot, listing, user_id)
    await callback.answer()


@router.callback_query(ListingCreateStates.confirm, F.data == "listing_confirm:edit")
async def listing_confirm_edit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ListingCreateStates.wait_photo)
    data = await state.get_data()
    code = data["listing_code"]
    await callback.message.answer(CODE_PROMPT.format(code=code), reply_markup=back_to_menu_keyboard())
    await callback.answer()


# back handled by global menu:main callback


# My listings: show list and handle "Посмотреть отклики" / "Закрыть заявку"
@router.message(F.text == "Мои заявки")
async def my_listings(message: Message, state: FSMContext, session):
    if not message.from_user:
        return
    await state.clear()
    await state.set_state(MAIN_MENU_STATE)
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not user:
        await message.answer("Сначала /start.", reply_markup=main_menu_keyboard())
        return
    listings = await get_open_listings_by_user(session, user.id)
    if not listings:
        await message.answer("У вас пока нет открытых заявок.", reply_markup=main_menu_keyboard())
        return
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    for lst in listings:
        caption = f"{user.first_name or 'Вы'} ({user.confirmed_deals} подтв. сделок)\nКод заявки «{lst.code}» (сравните с кодом на фото)\n{lst.description}"
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="Посмотреть отклики", callback_data=f"listings_resp:{lst.id}"),
            InlineKeyboardButton(text="Закрыть заявку", callback_data=f"listings_close:{lst.id}"),
        )
        await message.answer_photo(photo=lst.photo_file_id or "", caption=caption, reply_markup=builder.as_markup())
    await message.answer("У вас приостановлены входящие. Чтобы восстановить — вернитесь в главное меню.", reply_markup=back_to_menu_keyboard())


@router.callback_query(F.data == "menu:my_listings")
async def my_listings_callback(callback: CallbackQuery, state: FSMContext, session):
    if not callback.from_user:
        await callback.answer()
        return
    await state.clear()
    await state.set_state(MAIN_MENU_STATE)
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.message.answer("Сначала /start.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    listings = await get_open_listings_by_user(session, user.id)
    if not listings:
        await callback.message.answer("У вас пока нет открытых заявок.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    for lst in listings:
        caption = f"{user.first_name or 'Вы'} ({user.confirmed_deals} подтв. сделок)\nКод заявки «{lst.code}» (сравните с кодом на фото)\n{lst.description}"
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="Посмотреть отклики", callback_data=f"listings_resp:{lst.id}"),
            InlineKeyboardButton(text="Закрыть заявку", callback_data=f"listings_close:{lst.id}"),
        )
        await callback.message.answer_photo(photo=lst.photo_file_id or "", caption=caption, reply_markup=builder.as_markup())
    await callback.message.answer("У вас приостановлены входящие. Чтобы восстановить — вернитесь в главное меню.", reply_markup=back_to_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("listings_close:"))
async def listing_close_callback(callback: CallbackQuery, state: FSMContext, session, bot):
    listing_id = int(callback.data.split(":", 1)[1])
    if not callback.from_user:
        await callback.answer()
        return
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.answer("Ошибка.")
        return
    ok = await close_listing(session, listing_id, user.id)
    if ok:
        await _notify_listing_closed(session, bot, listing_id, user.id)
        await callback.message.edit_caption(callback.message.caption + "\n\n[Заявка закрыта]")
        await callback.answer("Заявка закрыта.")
    else:
        await callback.answer("Не удалось закрыть заявку.")


async def _notify_listing_closed(session, bot, listing_id: int, closed_by_user_id: int):
    """Notify the other side of matches on this listing that the listing was deleted."""
    from sqlalchemy import select
    from bot.models.match import Match
    from bot.models.user import User
    result = await session.execute(select(Match).where(Match.listing_id == listing_id))
    for match in result.scalars().all():
        other_id = match.response_owner_id if match.listing_owner_id == closed_by_user_id else match.listing_owner_id
        if other_id == closed_by_user_id:
            continue
        u = await session.get(User, other_id)
        if u:
            try:
                await bot.send_message(u.telegram_id, "Пользователь удалил заявку.")
            except Exception:
                pass
