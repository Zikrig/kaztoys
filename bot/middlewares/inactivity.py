import asyncio
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.fsm.context import FSMContext

from bot.config import load_config

config = load_config()
INACTIVITY_SECONDS = config.INACTIVITY_MINUTES * 60

# Per-user timer: user_id -> (asyncio.Task, last_activity_timestamp)
_user_timers: Dict[int, asyncio.Task] = {}

MAIN_MENU_STATE = "main_menu"


class InactivityMiddleware(BaseMiddleware):
    def __init__(self, default_state: str = MAIN_MENU_STATE):
        self.default_state = default_state

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        if user_id is None:
            return await handler(event, data)

        # Cancel previous timer
        if user_id in _user_timers:
            task = _user_timers.pop(user_id)
            task.cancel()

        state: FSMContext = data.get("state")
        if state is None:
            return await handler(event, data)
        bot = data.get("bot")

        async def reset_to_menu():
            await asyncio.sleep(INACTIVITY_SECONDS)
            _user_timers.pop(user_id, None)
            await state.clear()
            await state.set_state(self.default_state)
            if bot is not None:
                try:
                    from bot.keyboards.menu import main_menu_keyboard

                    await bot.send_message(
                        user_id,
                        "Вы были неактивны 10 минут. Возвращаем в главное меню.",
                        reply_markup=main_menu_keyboard(),
                    )
                except Exception:
                    pass

        task = asyncio.create_task(reset_to_menu())
        _user_timers[user_id] = task

        try:
            return await handler(event, data)
        finally:
            pass
