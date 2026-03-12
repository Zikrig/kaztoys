from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.services.report import is_user_blocked


class BlockedUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        session = data.get("session")
        if session is None:
            return await handler(event, data)

        telegram_id = None
        if isinstance(event, Message) and event.from_user:
            telegram_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            telegram_id = event.from_user.id

        if telegram_id is None:
            return await handler(event, data)

        if not await is_user_blocked(session, telegram_id):
            return await handler(event, data)

        if isinstance(event, Message):
            await event.answer("Ваш доступ к боту ограничен.")
        elif isinstance(event, CallbackQuery):
            await event.answer("Ваш доступ к боту ограничен.", show_alert=True)
        return None
