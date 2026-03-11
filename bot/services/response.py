import random
import string
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.response import Response
from bot.models.listing import Listing

CODE_LENGTH = 6
CODE_CHARS = string.digits + string.ascii_uppercase


async def generate_unique_response_code(session: AsyncSession, max_attempts: int = 20) -> str:
    for _ in range(max_attempts):
        code = "".join(random.choices(CODE_CHARS, k=CODE_LENGTH))
        r = await session.execute(select(Response.id).where(Response.code == code))
        if r.scalar_one_or_none() is not None:
            continue
        r2 = await session.execute(select(Listing.id).where(Listing.code == code))
        if r2.scalar_one_or_none() is not None:
            continue
        return code
    raise RuntimeError("Could not generate unique code")


async def create_response(
    session: AsyncSession,
    listing_id: int,
    user_id: int,
    code: str,
    photo_file_id: str,
    description: str,
) -> Response:
    resp = Response(
        listing_id=listing_id,
        user_id=user_id,
        code=code,
        photo_file_id=photo_file_id,
        description=description,
        chosen=False,
    )
    session.add(resp)
    await session.commit()
    await session.refresh(resp)
    return resp


async def get_responses_by_listing(session: AsyncSession, listing_id: int):
    result = await session.execute(
        select(Response).where(Response.listing_id == listing_id).order_by(Response.created_at.desc())
    )
    return result.scalars().all()


async def get_response_by_id(session: AsyncSession, response_id: int) -> Response | None:
    result = await session.execute(select(Response).where(Response.id == response_id))
    return result.scalar_one_or_none()


async def get_responses_by_user(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(Response).where(Response.user_id == user_id).order_by(Response.created_at.desc())
    )
    return result.scalars().all()
