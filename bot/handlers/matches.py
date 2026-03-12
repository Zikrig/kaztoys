from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards.menu import main_menu_keyboard
from bot.services.user import get_user_by_telegram_id
from bot.services.listing import get_listing_by_id
from bot.services.response import get_responses_by_listing, get_response_by_id
from bot.services.match import create_match, confirm_deal, cancel_deal, get_pending_matches_for_user, get_match_by_id
from bot.models.user import User
from bot.middlewares.inactivity import MAIN_MENU_STATE
from bot.texts.menu import BTN_OPEN_UNCONFIRMED

router = Router(name="matches")


async def send_pending_matches(message, session, user) -> bool:
    matches = await get_pending_matches_for_user(session, user.id)
    if not matches:
        return False
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    for match in matches:
        listing = await get_listing_by_id(session, match.listing_id)
        resp = await get_response_by_id(session, match.response_id)
        if not listing or not resp:
            continue
        text = f"Сделка. Заявка {listing.code} / Отклик {resp.code}."
        builder = None
        if match.reminder_sent:
            text += " Подтвердите или отмените сделку."
            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(text="Подтвердить сделку", callback_data=f"match_confirm:{match.id}"),
                InlineKeyboardButton(text="Сделка не состоялась", callback_data=f"match_cancel:{match.id}"),
            )
        else:
            text += " Подтверждение станет доступно после напоминания через 24 часа."
        await message.answer(text, reply_markup=builder.as_markup() if builder else None)
    return True


@router.message(F.text == BTN_OPEN_UNCONFIRMED)
async def open_unconfirmed_matches(message, state: FSMContext, session, bot: Bot):
    await state.clear()
    if not message.from_user:
        return
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not user:
        await message.answer("Сначала /start.", reply_markup=main_menu_keyboard())
        return
    has_matches = await send_pending_matches(message, session, user)
    if not has_matches:
        await message.answer("Нет неподтверждённых сделок.", reply_markup=main_menu_keyboard())
        return
    await message.answer("Вернитесь в меню.", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "menu:open_unconfirmed")
async def open_unconfirmed_matches_callback(callback: CallbackQuery, state: FSMContext, session, bot: Bot):
    await state.clear()
    if not callback.from_user:
        await callback.answer()
        return
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.message.answer("Сначала /start.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    has_matches = await send_pending_matches(callback.message, session, user)
    if not has_matches:
        await callback.message.answer("Нет неподтверждённых сделок.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    await callback.message.answer("Вернитесь в меню.", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("listings_resp:"))
async def show_responses_for_listing(callback: CallbackQuery, state: FSMContext, session):
    listing_id = int(callback.data.split(":", 1)[1])
    if not callback.from_user:
        await callback.answer()
        return
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.answer("Ошибка.")
        return
    listing = await get_listing_by_id(session, listing_id)
    if not listing or listing.user_id != user.id:
        await callback.answer("Нет доступа.")
        return
    responses = await get_responses_by_listing(session, listing_id)
    await callback.answer()
    if not responses:
        await callback.message.answer("По этой заявке пока нет откликов.")
        return
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    for resp in responses:
        cap = f"Код отклика {resp.code}. {resp.description}"
        builder = InlineKeyboardBuilder()
        if not resp.chosen:
            builder.row(InlineKeyboardButton(text="Выбрать", callback_data=f"choose_resp:{resp.id}"))
        await callback.message.answer_photo(
            photo=resp.photo_file_id or "",
            caption=cap,
            reply_markup=builder.as_markup() if not resp.chosen else None,
        )
    await callback.message.answer("Входящие приостановлены. Вернитесь в главное меню.", reply_markup=main_menu_keyboard())


@router.callback_query(F.data.startswith("choose_resp:"))
async def choose_response(callback: CallbackQuery, state: FSMContext, session, bot: Bot):
    response_id = int(callback.data.split(":", 1)[1])
    if not callback.from_user:
        await callback.answer()
        return
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.answer("Ошибка.")
        return
    resp = await get_response_by_id(session, response_id)
    if not resp or resp.chosen:
        await callback.answer("Отклик уже выбран или удалён.")
        return
    listing = await get_listing_by_id(session, resp.listing_id)
    if not listing or listing.user_id != user.id:
        await callback.answer("Нет доступа.")
        return
    match = await create_match(
        session,
        listing_id=listing.id,
        response_id=resp.id,
        listing_owner_id=user.id,
        response_owner_id=resp.user_id,
    )
    if not match:
        await callback.answer("Не удалось создать мэтч.")
        return
    from bot.models.user import User as UserModel
    response_owner = await session.get(UserModel, resp.user_id)
    listing_owner = user
    uname_r = (response_owner.username or "").lstrip("@") if response_owner else ""
    uname_o = (getattr(listing_owner, "username", None) or "").lstrip("@")
    link_to_respondent = f"https://t.me/{uname_r}" if uname_r else (f"tg://user?id={response_owner.telegram_id}" if response_owner else None)
    link_to_owner = f"https://t.me/{uname_o}" if uname_o else f"tg://user?id={listing_owner.telegram_id}"
    contact_respondent = f"Контакт второй стороны: {response_owner.first_name or 'Пользователь'}" + (f" (@{response_owner.username})" if response_owner and response_owner.username else "")
    contact_owner = f"Контакт второй стороны: {listing_owner.first_name or 'Пользователь'}" + (f" (@{listing_owner.username})" if getattr(listing_owner, "username", None) else "")
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder_owner = InlineKeyboardBuilder()
    if link_to_respondent:
        builder_owner.row(InlineKeyboardButton(text="Связаться", url=link_to_respondent))
    builder_respondent = InlineKeyboardBuilder()
    builder_respondent.row(InlineKeyboardButton(text="Связаться", url=link_to_owner))
    try:
        await bot.send_message(callback.from_user.id, contact_respondent, reply_markup=builder_owner.as_markup() if link_to_respondent else None)
    except Exception:
        pass
    if response_owner:
        try:
            await bot.send_message(response_owner.telegram_id, contact_owner, reply_markup=builder_respondent.as_markup())
        except Exception:
            pass
    await callback.answer("Мэтч создан. Обоим отправлены контакты.")
    await callback.message.edit_caption(callback.message.caption + "\n\n[Выбрано]")


@router.callback_query(F.data.startswith("match_confirm:"))
async def match_confirm_callback(callback: CallbackQuery, session, bot: Bot):
    match_id = int(callback.data.split(":", 1)[1])
    if not callback.from_user:
        await callback.answer()
        return
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.answer("Ошибка.")
        return
    match = await get_match_by_id(session, match_id)
    if not match or not match.reminder_sent:
        await callback.answer("Подтверждение станет доступно после напоминания через 24 часа.")
        return
    ok = await confirm_deal(session, match_id, user.id)
    if ok:
        match = await get_match_by_id(session, match_id)
        if match and match.status == "both_confirmed":
            from bot.models.user import User as UserModel
            owner = await session.get(UserModel, match.listing_owner_id)
            respondent = await session.get(UserModel, match.response_owner_id)
            thanks = "Спасибо за обратную связь!"
            if owner:
                try:
                    await bot.send_message(owner.telegram_id, thanks)
                except Exception:
                    pass
            if respondent:
                try:
                    await bot.send_message(respondent.telegram_id, thanks)
                except Exception:
                    pass
        await callback.answer("Подтверждение учтено.")
        await callback.message.edit_reply_markup(reply_markup=None)
    else:
        await callback.answer("Уже подтверждено или отменено.")


@router.callback_query(F.data.startswith("match_cancel:"))
async def match_cancel_callback(callback: CallbackQuery, session):
    match_id = int(callback.data.split(":", 1)[1])
    if not callback.from_user:
        await callback.answer()
        return
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.answer("Ошибка.")
        return
    match = await get_match_by_id(session, match_id)
    if not match or not match.reminder_sent:
        await callback.answer("Отмена станет доступна после напоминания через 24 часа.")
        return
    ok = await cancel_deal(session, match_id, user.id)
    if ok:
        await callback.answer("Сделка отменена.")
        await callback.message.edit_reply_markup(reply_markup=None)
    else:
        await callback.answer("Уже обработано.")
