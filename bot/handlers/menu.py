from sqlalchemy import select
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.models.user import User
from bot.models.match import Match
from bot.texts.menu import (
    MAIN_MENU_GREETING,
    UNCONFIRMED_MATCHES_REMINDER,
    BTN_BACK_TO_MENU,
)
from bot.keyboards.menu import main_menu_keyboard
from bot.middlewares.inactivity import MAIN_MENU_STATE
from bot.handlers.matches import send_pending_matches

router = Router(name="menu")


@router.message(F.text == BTN_BACK_TO_MENU)
async def to_main_menu(message: Message, state: FSMContext, session):
    await state.clear()
    await state.set_state(MAIN_MENU_STATE)
    await message.answer(MAIN_MENU_GREETING, reply_markup=main_menu_keyboard())
    if message.from_user:
        user_result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_result.scalar_one_or_none()
        if user:
            has_matches = await send_pending_matches(message, session, user)
            if has_matches:
                await message.answer(UNCONFIRMED_MATCHES_REMINDER)


@router.callback_query(F.data == "menu:main")
async def to_main_menu_callback(callback: CallbackQuery, state: FSMContext, session):
    await state.clear()
    await state.set_state(MAIN_MENU_STATE)
    await callback.message.answer(MAIN_MENU_GREETING, reply_markup=main_menu_keyboard())
    if callback.from_user:
        user_result = await session.execute(select(User).where(User.telegram_id == callback.from_user.id))
        user = user_result.scalar_one_or_none()
        if user:
            has_matches = await send_pending_matches(callback.message, session, user)
            if has_matches:
                await callback.message.answer(UNCONFIRMED_MATCHES_REMINDER)
    await callback.answer()




