import asyncio
import logging
import sys
from pathlib import Path

# Ensure project root is on path when running as module
if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("bot")

from bot.config import load_config
from bot.models.base import init_async_engine
from bot.handlers import (
    start_router,
    menu_router,
    listing_router,
    search_router,
    response_router,
    matches_router,
    subscription_router,
    support_router,
)
from bot.middlewares.db import DbSessionMiddleware
from bot.middlewares.bot import BotInjectMiddleware
from bot.middlewares.inactivity import InactivityMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware


async def wait_for_db(max_attempts: int = 30, interval: float = 2.0) -> bool:
    from sqlalchemy import text
    config = load_config()
    init_async_engine(config.DATABASE_URL)
    from bot.models.base import engine
    for i in range(max_attempts):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            if i == max_attempts - 1:
                raise
            await asyncio.sleep(interval)
    return False


def run_migrations():
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parent.parent,
        env={**__import__("os").environ},
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Migration stderr:", result.stderr, file=sys.stderr)
        raise RuntimeError(f"Migrations failed: {result.returncode}")


async def main():
    config = load_config()
    log.info("Waiting for database...")
    await wait_for_db()
    log.info("Running migrations...")
    run_migrations()
    log.info("Starting bot...")
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.message.middleware(BotInjectMiddleware(bot))
    dp.callback_query.middleware(BotInjectMiddleware(bot))
    dp.message.middleware(InactivityMiddleware())
    dp.callback_query.middleware(InactivityMiddleware())
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())

    dp.include_router(start_router)
    dp.include_router(listing_router)
    dp.include_router(search_router)
    dp.include_router(response_router)
    dp.include_router(matches_router)
    dp.include_router(subscription_router)
    dp.include_router(support_router)
    dp.include_router(menu_router)

    from bot.tasks.reminder_24h import run_reminder_cycle

    async def reminder_loop():
        while True:
            await asyncio.sleep(600)
            try:
                await run_reminder_cycle(bot)
            except Exception as e:
                log.exception("Reminder 24h task error: %s", e)

    asyncio.create_task(reminder_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
