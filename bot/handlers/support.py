from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot.config import load_config
from bot.texts.menu import BTN_SUPPORT
from bot.keyboards.menu import main_menu_keyboard

router = Router(name="support")
config = load_config()


@router.message(F.text == BTN_SUPPORT)
async def support(message: Message, state: FSMContext):
    await state.clear()
    contact = config.SUPPORT_CONTACT
    await message.answer(
        f"Связаться с поддержкой: {contact}",
        reply_markup=main_menu_keyboard(),
    )
