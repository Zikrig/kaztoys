import asyncio
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

# Simple in-memory throttling: user_id -> last message time
_last_message: Dict[int, float] = {}
THROTTLE_SECONDS = 0.5


class ThrottlingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None) or getattr(getattr(event, "message", None), "from_user", None)
        if user is None:
            return await handler(event, data)

        uid = user.id
        now = asyncio.get_event_loop().time()
        last = _last_message.get(uid, 0)
        if now - last < THROTTLE_SECONDS:
            return
        _last_message[uid] = now
        return await handler(event, data)
