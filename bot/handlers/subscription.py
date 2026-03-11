from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot.texts.menu import BTN_MY_SUBSCRIPTION
from bot.keyboards.menu import main_menu_keyboard
from bot.services.user import get_user_by_telegram_id
from bot.services.subscription import get_active_subscription

router = Router(name="subscription")


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
