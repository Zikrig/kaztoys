import random
import string
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.listing import Listing
from bot.models.response import Response


CODE_LENGTH = 6
CODE_CHARS = string.digits + string.ascii_uppercase


async def generate_unique_code(session: AsyncSession, max_attempts: int = 20) -> str:
    for _ in range(max_attempts):
        code = "".join(random.choices(CODE_CHARS, k=CODE_LENGTH))
        r1 = await session.execute(select(Listing.id).where(Listing.code == code))
        if r1.scalar_one_or_none() is not None:
            continue
        r2 = await session.execute(select(Response.id).where(Response.code == code))
        if r2.scalar_one_or_none() is not None:
            continue
        return code
    raise RuntimeError("Could not generate unique code")


async def create_listing(
    session: AsyncSession,
    user_id: int,
    code: str,
    photo_file_id: str,
    category: str,
    age_group: str,
    district: str | None,
    description: str,
) -> Listing:
    listing = Listing(
        user_id=user_id,
        code=code,
        photo_file_id=photo_file_id,
        category=category,
        age_group=age_group,
        district=district,
        description=description,
        status="open",
    )
    session.add(listing)
    await session.commit()
    await session.refresh(listing)
    return listing


async def update_listing(
    session: AsyncSession,
    listing_id: int,
    photo_file_id: str | None = None,
    category: str | None = None,
    age_group: str | None = None,
    district: str | None = None,
    description: str | None = None,
) -> Listing | None:
    result = await session.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        return None
    if photo_file_id is not None:
        listing.photo_file_id = photo_file_id
    if category is not None:
        listing.category = category
    if age_group is not None:
        listing.age_group = age_group
    if district is not None:
        listing.district = district
    if description is not None:
        listing.description = description
    await session.commit()
    await session.refresh(listing)
    return listing


async def get_listing_by_id(session: AsyncSession, listing_id: int) -> Listing | None:
    result = await session.execute(select(Listing).where(Listing.id == listing_id))
    return result.scalar_one_or_none()


async def get_open_listings_by_user(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(Listing).where(Listing.user_id == user_id, Listing.status == "open").order_by(Listing.created_at.desc())
    )
    return result.scalars().all()


async def close_listing(session: AsyncSession, listing_id: int, user_id: int) -> bool:
    result = await session.execute(select(Listing).where(Listing.id == listing_id, Listing.user_id == user_id))
    listing = result.scalar_one_or_none()
    if not listing:
        return False
    listing.status = "closed"
    await session.commit()
    return True
