from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.user import User


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    referral_from_id: int | None = None,
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is not None:
        user.username = username or user.username
        user.first_name = first_name or user.first_name
        if referral_from_id is not None and user.referral_from_id is None:
            user.referral_from_id = referral_from_id
        await session.commit()
        await session.refresh(user)
        return user
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        referral_from_id=referral_from_id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def increment_confirmed_deals(session: AsyncSession, user_id: int, count: int = 1) -> None:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.confirmed_deals = (user.confirmed_deals or 0) + count
        await session.commit()


async def mark_onboarding_done(session: AsyncSession, user_id: int) -> None:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user and not user.onboarding_done:
        user.onboarding_done = True
        await session.commit()
