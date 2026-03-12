from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.user import User


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
    referral_from_id: int | None = None,
    acquisition_source: str = "other",
) -> tuple[User, bool]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user is not None:
        user.username = username or user.username
        user.first_name = first_name or user.first_name
        if referral_from_id is not None and user.referral_from_id is None:
            user.referral_from_id = referral_from_id
            user.acquisition_source = "referral"
        await session.commit()
        await session.refresh(user)
        return user, False
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        referral_from_id=referral_from_id,
        acquisition_source=acquisition_source,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user, True


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


async def get_referrals_count_by_user(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count(User.id)).where(User.referral_from_id == user_id)
    )
    return int(result.scalar_one() or 0)


async def get_users_acquisition_counts(session: AsyncSession) -> dict[str, int]:
    rows = await session.execute(
        select(User.acquisition_source, func.count(User.id)).group_by(User.acquisition_source)
    )
    counts = {"referral": 0, "instagram": 0, "other": 0}
    for source, count in rows.all():
        key = source if source in counts else "other"
        counts[key] += int(count or 0)
    return counts
