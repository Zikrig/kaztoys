from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, FSInputFile, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.config import load_config
from bot.texts.onboarding import DISCLAIMER, READY_TO_START, BTN_START_SEARCH, BTN_ACCEPT, BTN_LIST_LISTING
from bot.texts.menu import MAIN_MENU_GREETING
from bot.keyboards.menu import main_menu_keyboard
from bot.services.user import get_or_create_user, mark_onboarding_done
from bot.services.subscription import add_subscription_days
from bot.models.user import User
from bot.middlewares.inactivity import MAIN_MENU_STATE

router = Router(name="start")
config = load_config()


class OnboardingStates(StatesGroup):
    wait_accept = State()
    wait_ready_choice = State()


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    session,
):
    from_user = message.from_user
    if not from_user:
        return
    telegram_id = from_user.id
    username = from_user.username
    first_name = from_user.first_name

    referral_from_id = None
    acquisition_source = "other"
    payload = message.text
    if isinstance(payload, str) and config.REFERRAL_PARAM:
        # /start ref_123 or /start 123 (deep link)
        parts = payload.split()
        if len(parts) >= 2:
            ref_part = parts[1]
            if ref_part.startswith(f"{config.REFERRAL_PARAM}_"):
                try:
                    ref_id = int(ref_part.split("_", 1)[1])
                    referral_from_id = ref_id
                    acquisition_source = "referral"
                except (ValueError, IndexError):
                    pass
            elif ref_part.isdigit():
                referral_from_id = int(ref_part)
                acquisition_source = "referral"
            elif ref_part == config.INSTAGRAM_PARAM or ref_part.startswith(f"{config.INSTAGRAM_PARAM}_"):
                acquisition_source = "instagram"
    if referral_from_id is not None:
        referrer = await session.get(User, referral_from_id)
        if not referrer:
            referral_from_id = None
            if acquisition_source == "referral":
                acquisition_source = "other"

    user, created = await get_or_create_user(
        session,
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        referral_from_id=referral_from_id,
        acquisition_source=acquisition_source,
    )
    if created and user.referral_from_id and user.referral_from_id != user.id:
        referrer = await session.get(User, user.referral_from_id)
        if referrer:
            await add_subscription_days(session, referrer.id, config.REFERRAL_BONUS_DAYS)

    await state.clear()
    await state.set_state(MAIN_MENU_STATE)

    # New user onboarding: disclaimer -> video -> ready?
    # We consider "new" if we just created the user (no updated_at difference) or check created_at
    # Simple approach: always show onboarding for /start; if we want "returning" skip to menu we can check something
    # Per doc: first time = disclaimer + video + "Ready?"; returning = main menu
    # So we need to know if user already completed onboarding. Easiest: check if user has any listings or has been updated (e.g. last_seen). For simplicity we'll show onboarding only when created_at is very recent (same minute) or add a flag. Actually doc says: "Пользователь нажимает /start (первый раз)" vs "уже был в боте". So we need a way to know. Simplest: add onboarding_done to User or check created_at != updated_at or subscriptions. For minimal implementation let's show onboarding only when user was just created (we could set a flag in get_or_create_user). We'll add a field has_done_onboarding to User. For now to avoid migration, we can check: if user has no listings and no search_filters and created_at is recent, show onboarding. Even simpler: always show disclaimer+video+ready on /start; after they click "Начать поиск" we go to search. Returning user: when they /start again we show main menu. So we need to distinguish. Easiest: store in FSM or in User a "onboarding_done". Let's add to User model: onboarding_done BOOLEAN DEFAULT FALSE. Then migration. Actually the first migration is already written - I'd need a second migration. Alternatively: consider user "returning" if updated_at > created_at + 1 minute or if they have any listing. For now let's do: if user has at least one listing OR we have search_filters, show main menu; else show onboarding. So first-time users (no listings, no filters) get onboarding.
    if user.onboarding_done:
        await message.answer(MAIN_MENU_GREETING, reply_markup=main_menu_keyboard())
        return

    await message.answer(DISCLAIMER, reply_markup=__accept_keyboard())
    await state.set_state(OnboardingStates.wait_accept)


def __accept_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=BTN_ACCEPT, callback_data="onboarding:accept"))
    return builder.as_markup()


def __ready_keyboard():
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=BTN_START_SEARCH, callback_data="onboarding:start_search"))
    builder.row(InlineKeyboardButton(text=BTN_LIST_LISTING, callback_data="onboarding:new_listing"))
    return builder.as_markup()


@router.callback_query(OnboardingStates.wait_accept, F.data == "onboarding:accept")
async def onboarding_accept_any(callback: CallbackQuery, state: FSMContext, session):
    if callback.from_user:
        from bot.services.user import get_user_by_telegram_id

        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if user:
            await mark_onboarding_done(session, user.id)
    await state.set_state(OnboardingStates.wait_ready_choice)
    video_path = config.video_path_resolved()
    if video_path.exists():
        video = FSInputFile(video_path)
        await callback.message.answer_video(video=video)
    else:
        await callback.message.answer("(Видео-инструкция будет добавлена позже)")
    await callback.message.answer(READY_TO_START, reply_markup=__ready_keyboard())
    await callback.answer()


@router.callback_query(OnboardingStates.wait_ready_choice, F.data == "onboarding:start_search")
async def onboarding_start_search(callback: CallbackQuery, state: FSMContext, session, bot):
    from bot.handlers.search import start_search
    await start_search(callback.message, state, session, bot)
    await callback.answer()


@router.callback_query(OnboardingStates.wait_ready_choice, F.data == "onboarding:new_listing")
async def onboarding_list_listing(callback: CallbackQuery, state: FSMContext, session, bot):
    from bot.handlers.listing import start_listing_create
    await start_listing_create(callback.message, state, session)
    await callback.answer()


@router.message(OnboardingStates.wait_ready_choice)
async def onboarding_ready_other(message: Message):
    await message.answer("Используйте inline-кнопки в предыдущем сообщении.")
