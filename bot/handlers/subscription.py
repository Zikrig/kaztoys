from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.texts.menu import BTN_MY_SUBSCRIPTION, BTN_REFERRAL
from bot.keyboards.menu import main_menu_keyboard
from bot.services.user import get_user_by_telegram_id, get_referrals_count_by_user
from bot.services.subscription import get_active_subscription
from bot.config import load_config

router = Router(name="subscription")
config = load_config()


@router.message(F.text == BTN_MY_SUBSCRIPTION)
async def my_subscription(message: Message, state: FSMContext, session):
    await state.clear()
    if not message.from_user:
        return
    user = await get_user_by_telegram_id(session, message.from_user.id)
    if not user:
        await message.answer("Сначала /start.", reply_markup=main_menu_keyboard())
        return
    sub = await get_active_subscription(session, user.id)
    if sub:
        now = datetime.now(timezone.utc)
        days_left = (sub.expires_at - now).days
        await message.answer(
            f"Тариф стандарт. Осталось {days_left} дн.",
            reply_markup=main_menu_keyboard(),
        )
    else:
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="Подключить", callback_data="sub_connect"))
        await message.answer(
            "У вас нет активной подписки. Подключите доступ на 2 недели.",
            reply_markup=builder.as_markup(),
        )


@router.callback_query(F.data == "menu:subscription")
async def my_subscription_callback(callback, state: FSMContext, session):
    await state.clear()
    if not callback.from_user:
        await callback.answer()
        return
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.message.answer("Сначала /start.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return
    sub = await get_active_subscription(session, user.id)
    if sub:
        now = datetime.now(timezone.utc)
        days_left = (sub.expires_at - now).days
        await callback.message.answer(
            f"Тариф стандарт. Осталось {days_left} дн.",
            reply_markup=main_menu_keyboard(),
        )
    else:
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="Подключить", callback_data="sub_connect"))
        await callback.message.answer(
            "У вас нет активной подписки. Подключите доступ на 2 недели.",
            reply_markup=builder.as_markup(),
        )
    await callback.answer()


@router.callback_query(F.data == "sub_connect")
async def sub_connect(callback, session):
    from bot.services.subscription import create_subscription
    if not callback.from_user:
        await callback.answer()
        return
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    if not user:
        await callback.answer()
        return
    await create_subscription(session, user.id, days=14)
    await callback.answer("Подписка на 2 недели подключена.")
    await callback.message.answer("Подписка подключена. Осталось 14 дней.", reply_markup=main_menu_keyboard())


def _build_referral_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start={config.REFERRAL_PARAM}_{user_id}"


async def _send_referral_info(target_message, session, telegram_user_id: int, bot) -> None:
    user = await get_user_by_telegram_id(session, telegram_user_id)
    if not user:
        await target_message.answer("Сначала /start.", reply_markup=main_menu_keyboard())
        return
    referrals_count = await get_referrals_count_by_user(session, user.id)
    me = await bot.get_me()
    if me.username:
        referral_link = _build_referral_link(me.username, user.id)
        link_line = f"Ваша ссылка: {referral_link}"
    else:
        link_line = "У бота нет username, реферальная ссылка недоступна."
    await target_message.answer(
        (
            "Реферальная программа\n\n"
            f"{link_line}\n"
            f"Приглашено пользователей: {referrals_count}\n"
            f"Бонус за каждого: +{config.REFERRAL_BONUS_DAYS} дн. подписки"
        ),
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == BTN_REFERRAL)
async def referral_info_message(message: Message, state: FSMContext, session, bot):
    await state.clear()
    if not message.from_user:
        return
    await _send_referral_info(message, session, message.from_user.id, bot)


@router.callback_query(F.data == "menu:referral")
async def referral_info_callback(callback: CallbackQuery, state: FSMContext, session, bot):
    await state.clear()
    if not callback.from_user:
        await callback.answer()
        return
    await _send_referral_info(callback.message, session, callback.from_user.id, bot)
    await callback.answer()
