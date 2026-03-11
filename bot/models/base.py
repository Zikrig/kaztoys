from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from bot.config import load_config

config = load_config()
engine = None
async_session_factory = None


class Base(DeclarativeBase):
    pass


def init_async_engine(database_url: str | None = None):
    global engine, async_session_factory
    url = database_url or config.DATABASE_URL
    engine = create_async_engine(
        url,
        echo=False,
    )
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return engine


def get_async_session_maker() -> async_sessionmaker[AsyncSession]:
    if async_session_factory is None:
        init_async_engine()
    return async_session_factory
