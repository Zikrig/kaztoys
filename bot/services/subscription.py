from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.subscription import Subscription


async def has_active_subscription(session: AsyncSession, user_id: int) -> bool:
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.expires_at > datetime.now(timezone.utc),
        ).order_by(Subscription.expires_at.desc()).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def get_active_subscription(session: AsyncSession, user_id: int) -> Subscription | None:
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.expires_at > datetime.now(timezone.utc),
        ).order_by(Subscription.expires_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def create_subscription(session: AsyncSession, user_id: int, days: int = 14) -> Subscription:
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=days)
    sub = Subscription(user_id=user_id, started_at=now, expires_at=expires)
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return sub
