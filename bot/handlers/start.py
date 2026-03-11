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
                except (ValueError, IndexError):
                    pass
            elif ref_part.isdigit():
                referral_from_id = int(ref_part)

    user = await get_or_create_user(
        session,
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        referral_from_id=referral_from_id,
    )

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
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_ACCEPT)]],
        resize_keyboard=True,
    )


def __ready_keyboard():
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_START_SEARCH)],
            [KeyboardButton(text=BTN_LIST_LISTING)],
        ],
        resize_keyboard=True,
    )


@router.message(OnboardingStates.wait_accept)
async def onboarding_accept_any(message: Message, state: FSMContext, session):
    if message.text != BTN_ACCEPT:
        await message.answer("Нажмите кнопку «Принять», чтобы продолжить.")
        return
    if message.from_user:
        from bot.services.user import get_user_by_telegram_id

        user = await get_user_by_telegram_id(session, message.from_user.id)
        if user:
            await mark_onboarding_done(session, user.id)
    await state.set_state(OnboardingStates.wait_ready_choice)
    video_path = config.video_path_resolved()
    if video_path.exists():
        video = FSInputFile(video_path)
        await message.answer_video(video=video)
    else:
        await message.answer("(Видео-инструкция будет добавлена позже)")
    await message.answer(READY_TO_START, reply_markup=__ready_keyboard())


@router.message(OnboardingStates.wait_ready_choice, F.text == BTN_START_SEARCH)
async def onboarding_start_search(message: Message, state: FSMContext, session, bot):
    from bot.handlers.search import start_search
    await start_search(message, state, session, bot)


@router.message(OnboardingStates.wait_ready_choice, F.text == BTN_LIST_LISTING)
async def onboarding_list_listing(message: Message, state: FSMContext, session, bot):
    from bot.handlers.listing import start_listing_create
    await start_listing_create(message, state, session)


@router.message(OnboardingStates.wait_ready_choice)
async def onboarding_ready_other(message: Message):
    await message.answer("Выберите «Начать поиск» или «Выставить свою игрушку».")
