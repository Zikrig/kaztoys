import asyncio
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import BaseEventIsolation

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
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id if event.from_user else None
        if user_id is None:
            return await handler(event, data)

        # Cancel previous timer
        if user_id in _user_timers:
            task = _user_timers.pop(user_id)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        state: FSMContext = data.get("state")
        if state is None:
            return await handler(event, data)

        async def reset_to_menu():
            await asyncio.sleep(INACTIVITY_SECONDS)
            _user_timers.pop(user_id, None)
            await state.clear()
            await state.set_state(self.default_state)

        task = asyncio.create_task(reset_to_menu())
        _user_timers[user_id] = task

        try:
            return await handler(event, data)
        finally:
            pass
