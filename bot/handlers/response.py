from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.texts.menu import BTN_BACK_TO_MENU, BTN_CANCEL, BTN_MY_RESPONSES
from bot.keyboards.menu import main_menu_keyboard
from bot.keyboards.common import back_to_menu_keyboard, cancel_keyboard
from bot.keyboards.report import report_button_row
from bot.texts.listing import BTN_CONFIRM_SEND, BTN_EDIT
from bot.services.user import get_user_by_telegram_id
from bot.services.listing import get_open_listings_by_user, get_listing_by_id
from bot.services.response import (
    generate_unique_response_code,
    create_response,
    get_responses_by_listing,
    get_responses_by_user,
)
from bot.services.subscription import has_active_subscription, create_subscription
from bot.models.listing import Listing
from bot.models.user import User
from bot.middlewares.inactivity import MAIN_MENU_STATE

router = Router(name="response")


class ResponseStates(StatesGroup):
    choose_listing = State()
    wait_photo = State()
    wait_description = State()
    confirm = State()


async def _show_response_source_picker(callback: CallbackQuery, session, user_id: int):
    listings = await get_open_listings_by_user(session, user_id)
    if not listings:
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="Создать новый отклик", callback_data="resp_create_new"))
        await callback.message.answer(
            "У вас нет открытых заявок. Можно создать новый отклик вручную.",
            reply_markup=builder.as_markup(),
        )
        return

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    for lst in listings:
        builder.row(InlineKeyboardButton(text=f"Отправить эту: {lst.code}", callback_data=f"resp_use:{lst.id}"))
    builder.row(InlineKeyboardButton(text="Создать новый отклик", callback_data="resp_create_new"))
    await callback.message.answer(
        "Выберите имеющуюся заявку или создайте новый отклик для этой заявки:",
        reply_markup=builder.as_markup(),
    )


async def _prompt_response_subscription(callback: CallbackQuery):
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Купить доступ на 2 недели", callback_data="response_buy_sub"))
    builder.row(InlineKeyboardButton(text="В главное меню", callback_data="menu:main"))
    await callback.message.answer(
        "Для обмена нужна активная подписка. Подключить доступ на 2 недели?",
        reply_markup=builder.as_markup(),
    )


@router.message(F.text == BTN_MY_RESPONSES)
async def my_responses(message: Message, state: FSMContext, session):
    await state.clear()
    if not message.from_user:
        return
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not user:
        await message.answer("Сначала /start.", reply_markup=main_menu_keyboard())
        return
    responses = await get_responses_by_user(session, user.id)
    if not responses:
        await message.answer("У вас пока нет откликов.", reply_markup=main_menu_keyboard())
        return
    from bot.models.user import User as UserModel
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    for resp in responses:
        listing = await get_listing_by_id(session, resp.listing_id)
        if not listing:
            continue
        owner = await session.get(UserModel, listing.user_id)
        name = (owner.first_name or "Пользователь") if owner else "Пользователь"
        deals = (owner.confirmed_deals or 0) if owner else 0
        status = "Ожидает выбора" if not resp.chosen else f"Выбран (заявка от {name})"
        caption = (
            f"{name} ({deals} подтв. сделок)\n"
            f"Код заявки {listing.code}. {listing.description}\n\n"
            f"Ваш отклик. Код {resp.code}. {resp.description}\n\n"
            f"Статус: {status}"
        )
        try:
            builder = InlineKeyboardBuilder()
            builder.row(*report_button_row(listing_id=listing.id))
            await message.answer_photo(photo=listing.photo_file_id or "", caption=caption, reply_markup=builder.as_markup())
            await message.answer_photo(photo=resp.photo_file_id or "")
        except Exception:
            await message.answer(caption)
    await message.answer("Вернитесь в меню.", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "menu:my_responses")
async def my_responses_callback(callback: CallbackQuery, state: FSMContext, session):
    if not callback.from_user:
        await callback.answer()
        return
    await state.clear()
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.message.answer("Сначала /start.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    responses = await get_responses_by_user(session, user.id)
    if not responses:
        await callback.message.answer("У вас пока нет откликов.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    from bot.models.user import User as UserModel
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    for resp in responses:
        listing = await get_listing_by_id(session, resp.listing_id)
        if not listing:
            continue
        owner = await session.get(UserModel, listing.user_id)
        name = (owner.first_name or "Пользователь") if owner else "Пользователь"
        deals = (owner.confirmed_deals or 0) if owner else 0
        status = "Ожидает выбора" if not resp.chosen else f"Выбран (заявка от {name})"
        caption = (
            f"{name} ({deals} подтв. сделок)\n"
            f"Код заявки {listing.code}. {listing.description}\n\n"
            f"Ваш отклик. Код {resp.code}. {resp.description}\n\n"
            f"Статус: {status}"
        )
        try:
            builder = InlineKeyboardBuilder()
            builder.row(*report_button_row(listing_id=listing.id))
            await callback.message.answer_photo(
                photo=listing.photo_file_id or "",
                caption=caption,
                reply_markup=builder.as_markup(),
            )
            await callback.message.answer_photo(photo=resp.photo_file_id or "")
        except Exception:
            await callback.message.answer(caption)
    await callback.message.answer("Вернитесь в меню.", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.message(F.text == "Предложить обмен")
async def response_offer_ignore(message: Message):
    await message.answer("Нажмите кнопку «Предложить обмен» под заявкой в поиске.")


@router.callback_query(F.data.startswith("search_offer:"))
async def response_after_search_offer(callback: CallbackQuery, state: FSMContext, session):
    listing_id = int(callback.data.split(":", 1)[1])
    if not callback.from_user:
        await callback.answer()
        return
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.message.answer("Сначала /start.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    active = await has_active_subscription(session, user.id)
    await state.update_data(target_listing_id=listing_id)
    if not active:
        await callback.answer()
        await _prompt_response_subscription(callback)
        return
    target_listing = await get_listing_by_id(session, listing_id)
    if not target_listing:
        await callback.answer("Заявка не найдена.")
        return
    if target_listing.user_id == user.id:
        await callback.answer("Нельзя откликнуться на собственную заявку.")
        return
    await state.set_state(ResponseStates.choose_listing)
    await callback.answer()
    await _show_response_source_picker(callback, session, user.id)


@router.callback_query(F.data == "response_buy_sub")
async def response_buy_sub(callback: CallbackQuery, state: FSMContext, session):
    if not callback.from_user:
        await callback.answer()
        return
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.answer("Сначала нажмите /start.")
        return
    await create_subscription(session, user.id, days=14)
    await state.set_state(ResponseStates.choose_listing)
    await callback.answer("Подписка подключена.")
    await _show_response_source_picker(callback, session, user.id)


@router.callback_query(F.data.startswith("resp_use:"))
async def response_use_listing(callback: CallbackQuery, state: FSMContext, session, bot: Bot):
    my_listing_id = int(callback.data.split(":", 1)[1])
    data = await state.get_data()
    target_listing_id = data.get("target_listing_id")
    if not target_listing_id:
        await callback.answer("Сессия истекла. Начните поиск заново.")
        return
    target_listing = await get_listing_by_id(session, target_listing_id)
    if not target_listing or target_listing.status != "open":
        await callback.answer("Заявка уже закрыта.")
        return
    if not callback.from_user:
        await callback.answer()
        return
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.answer()
        return
    my_listing = await get_listing_by_id(session, my_listing_id)
    if not my_listing or my_listing.user_id != user.id:
        await callback.answer("Ошибка выбора.")
        return
    code = await generate_unique_response_code(session)
    await state.update_data(
        response_code=code,
        response_photo_file_id=my_listing.photo_file_id or "",
        response_description=my_listing.description,
        response_source="existing",
    )
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=BTN_CONFIRM_SEND, callback_data="response_confirm:send"),
        InlineKeyboardButton(text=BTN_EDIT, callback_data="response_confirm:edit"),
    )
    builder.row(InlineKeyboardButton(text=BTN_BACK_TO_MENU, callback_data="menu:main"))
    preview = (
        f"Код отклика: {code}\n"
        f"На заявку: {target_listing.code}\n"
        f"Описание: {my_listing.description}\n\n"
        "Подтвердите отправку отклика."
    )
    await state.set_state(ResponseStates.confirm)
    await callback.answer()
    await callback.message.answer_photo(
        photo=my_listing.photo_file_id or "",
        caption=preview,
        reply_markup=builder.as_markup(),
    )


def _contact_link(user: User) -> str:
    if user.username:
        return f"https://t.me/{user.username.lstrip('@')}"
    return f"tg://user?id={user.telegram_id}"


async def _notify_listing_owner_about_response(session, bot: Bot, listing, response, response_user: User):
    """По ТЗ: при отклике только владельцу заявки — уведомление с кнопкой «Выбрать этого»."""
    from bot.models.user import User as UserModel
    owner = await session.get(UserModel, listing.user_id)
    if not owner:
        return
    text = (
        "НА ВАШУ ЗАЯВКУ ПОСТУПИЛ ОТКЛИК!\n\n"
        f"Ваша заявка. Код {listing.code}. {listing.description}\n\n"
        f"Поступивший отклик. Код {response.code}. {response.description}"
    )
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Выбрать этого", callback_data=f"choose_resp:{response.id}"))
    try:
        await bot.send_photo(
            owner.telegram_id,
            photo=listing.photo_file_id or "",
            caption=text,
        )
        await bot.send_photo(
            owner.telegram_id,
            photo=response.photo_file_id or "",
        )
        await bot.send_message(
            owner.telegram_id,
            f"{response_user.first_name or 'Пользователь'} ({response_user.confirmed_deals or 0} подтв. сделок). Выберите отклик:",
            reply_markup=builder.as_markup(),
        )
    except Exception:
        pass


@router.callback_query(F.data == "resp_create_new")
async def response_create_new(callback: CallbackQuery, state: FSMContext, session):
    if not callback.from_user:
        await callback.answer()
        return
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.answer("Сначала нажмите /start.")
        return
    active = await has_active_subscription(session, user.id)
    if not active:
        await callback.answer()
        await _prompt_response_subscription(callback)
        return
    code = await generate_unique_response_code(session)
    await state.update_data(response_code=code, response_source="new")
    await state.set_state(ResponseStates.wait_photo)
    await callback.message.answer(
        f"Код отклика: {code}. Сделайте фото игрушки с бумажкой с этим кодом и отправьте фото.",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(ResponseStates.wait_photo, F.photo)
async def response_photo_received(message: Message, state: FSMContext, session):
    file_id = message.photo[-1].file_id
    await state.update_data(response_photo_file_id=file_id)
    await state.set_state(ResponseStates.wait_description)
    await message.answer("Напишите описание игрушки и сообщение продавцу одним сообщением.")


@router.message(ResponseStates.wait_photo, F.text == BTN_CANCEL)
async def response_back(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(MAIN_MENU_STATE)
    await message.answer("Главное меню.", reply_markup=main_menu_keyboard())


@router.message(ResponseStates.wait_description, F.text)
async def response_description_received(message: Message, state: FSMContext, session, bot: Bot):
    if message.text == BTN_CANCEL:
        await state.clear()
        await state.set_state(MAIN_MENU_STATE)
        await message.answer("Главное меню.", reply_markup=main_menu_keyboard())
        return
    data = await state.get_data()
    target_listing_id = data.get("target_listing_id")
    if not target_listing_id:
        await message.answer("Сессия истекла.", reply_markup=main_menu_keyboard())
        return
    target_listing = await get_listing_by_id(session, target_listing_id)
    if not target_listing or target_listing.status != "open":
        await message.answer("Заявка закрыта.", reply_markup=main_menu_keyboard())
        return
    if not message.from_user:
        return
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not user:
        return
    code = data["response_code"]
    photo_file_id = data["response_photo_file_id"]
    description = message.text
    await state.update_data(response_description=description)
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=BTN_CONFIRM_SEND, callback_data="response_confirm:send"),
        InlineKeyboardButton(text=BTN_EDIT, callback_data="response_confirm:edit"),
    )
    builder.row(InlineKeyboardButton(text=BTN_BACK_TO_MENU, callback_data="menu:main"))
    preview = (
        f"Код отклика: {code}\n"
        f"На заявку: {target_listing.code}\n"
        f"Описание: {description}\n\n"
        "Подтвердите отправку отклика."
    )
    await state.set_state(ResponseStates.confirm)
    await message.answer_photo(photo=photo_file_id, caption=preview, reply_markup=builder.as_markup())


@router.callback_query(ResponseStates.confirm, F.data == "response_confirm:send")
async def response_confirm_send(callback: CallbackQuery, state: FSMContext, session, bot: Bot):
    data = await state.get_data()
    target_listing_id = data.get("target_listing_id")
    if not target_listing_id or not callback.from_user:
        await state.clear()
        await state.set_state(MAIN_MENU_STATE)
        await callback.message.answer("Сессия истекла.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    target_listing = await get_listing_by_id(session, target_listing_id)
    if not target_listing or target_listing.status != "open":
        await state.clear()
        await state.set_state(MAIN_MENU_STATE)
        await callback.message.answer("Заявка закрыта.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    if not callback.from_user:
        await callback.answer()
        return
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        return
    resp = await create_response(
        session,
        listing_id=target_listing_id,
        user_id=user.id,
        code=data["response_code"],
        photo_file_id=data["response_photo_file_id"],
        description=data["response_description"],
    )
    await _notify_listing_owner_about_response(session, bot, target_listing, resp, user)
    if data.get("search_user_id"):
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from bot.texts.search import BTN_CONTINUE_SEARCH, BTN_NO_BACK_MENU
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text=BTN_CONTINUE_SEARCH, callback_data="search_continue_after_response"),
            InlineKeyboardButton(text=BTN_NO_BACK_MENU, callback_data="search_back_menu"),
        )
        await callback.message.answer("Отклик отправлен. Продолжить поиск?", reply_markup=builder.as_markup())
    else:
        await state.clear()
        await state.set_state(MAIN_MENU_STATE)
        await callback.message.answer("Отклик отправлен.", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(ResponseStates.confirm, F.data == "response_confirm:edit")
async def response_confirm_edit(callback: CallbackQuery, state: FSMContext, session):
    data = await state.get_data()
    if data.get("response_source") == "existing":
        if not callback.from_user:
            return
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            return
        listings = await get_open_listings_by_user(session, user.id)
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        for lst in listings:
            builder.row(InlineKeyboardButton(text=f"Отправить эту: {lst.code}", callback_data=f"resp_use:{lst.id}"))
        builder.row(InlineKeyboardButton(text="Создать новый отклик", callback_data="resp_create_new"))
        await state.set_state(ResponseStates.choose_listing)
        await callback.message.answer(
            "Выберите имеющуюся заявку или создайте новый отклик для этой заявки:",
            reply_markup=builder.as_markup(),
        )
        await callback.answer()
        return
    await state.set_state(ResponseStates.wait_photo)
    await callback.message.answer(
        f"Код отклика: {data['response_code']}. Сделайте фото игрушки с бумажкой с этим кодом и отправьте фото.",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


# back handled by global menu:main callback
