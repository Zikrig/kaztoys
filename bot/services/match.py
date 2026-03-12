from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.match import Match
from bot.models.response import Response
from bot.models.listing import Listing
from bot.models.user import User


async def create_match(
    session: AsyncSession,
    listing_id: int,
    response_id: int,
    listing_owner_id: int,
    response_owner_id: int,
) -> Match | None:
    resp = await session.get(Response, response_id)
    if not resp or resp.chosen:
        return None
    match = Match(
        listing_id=listing_id,
        response_id=response_id,
        listing_owner_id=listing_owner_id,
        response_owner_id=response_owner_id,
        status="pending",
    )
    session.add(match)
    resp.chosen = True
    await session.commit()
    await session.refresh(match)
    return match


async def get_match_by_id(session: AsyncSession, match_id: int) -> Match | None:
    return await session.get(Match, match_id)


async def confirm_deal(session: AsyncSession, match_id: int, user_id: int) -> bool:
    match = await session.get(Match, match_id)
    if not match or match.status != "pending":
        return False
    if match.listing_owner_id == user_id:
        match.listing_owner_confirmed = True
    elif match.response_owner_id == user_id:
        match.response_owner_confirmed = True
    else:
        return False
    listing = await session.get(Listing, match.listing_id)
    if listing and listing.status == "open":
        # As soon as one side confirms the exchange, hide the listing from active feeds.
        listing.status = "closed"
    if match.listing_owner_confirmed and match.response_owner_confirmed:
        match.status = "both_confirmed"
        from bot.services.user import increment_confirmed_deals
        await increment_confirmed_deals(session, match.listing_owner_id, 1)
        await increment_confirmed_deals(session, match.response_owner_id, 1)
    await session.commit()
    return True


async def cancel_deal(session: AsyncSession, match_id: int, user_id: int) -> bool:
    match = await session.get(Match, match_id)
    if not match or match.status != "pending":
        return False
    if match.listing_owner_id != user_id and match.response_owner_id != user_id:
        return False
    match.status = "one_cancelled"
    await session.commit()
    return True


async def get_pending_matches_for_user(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(Match).where(
            ((Match.listing_owner_id == user_id) | (Match.response_owner_id == user_id)),
            Match.status == "pending",
        )
    )
    return result.scalars().all()


async def get_matches_for_reminder(session: AsyncSession, *, after_hours: float = 24.0):
    """Matches created at least after_hours ago, reminder not yet sent, status pending."""
    threshold = datetime.now(timezone.utc) - timedelta(hours=after_hours)
    result = await session.execute(
        select(Match).where(
            Match.status == "pending",
            Match.reminder_sent.is_(False),
            Match.created_at <= threshold,
        )
    )
    return result.scalars().all()


async def mark_reminder_sent(session: AsyncSession, match_id: int) -> None:
    match = await session.get(Match, match_id)
    if match:
        match.reminder_sent = True
        await session.commit()
