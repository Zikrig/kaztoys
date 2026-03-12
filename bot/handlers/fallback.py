from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot.keyboards.menu import main_menu_keyboard
from bot.middlewares.inactivity import MAIN_MENU_STATE

router = Router(name="fallback")


@router.message()
async def catch_all_menu(message: Message, state: FSMContext):
    """
    Самый последний роутер: возвращает пользователя в главное меню,
    если сообщение не обработано ни одним из предыдущих роутеров.
    """
    await state.clear()
    await state.set_state(MAIN_MENU_STATE)
    await message.answer("Возвращаю вас в главное меню.", reply_markup=main_menu_keyboard())
