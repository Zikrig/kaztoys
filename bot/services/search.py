from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.listing import Listing
from bot.models.user import User
from bot.models.search_filters import SearchFilters
from bot.services.report import apply_listing_visibility_filters


async def save_search_filters(
    session: AsyncSession,
    user_id: int,
    category: str | None,
    age_group: str | None,
    district: str | None,
) -> None:
    result = await session.execute(select(SearchFilters).where(SearchFilters.user_id == user_id))
    sf = result.scalar_one_or_none()
    if sf:
        sf.category = category
        sf.age_group = age_group
        sf.district = district
    else:
        sf = SearchFilters(user_id=user_id, category=category, age_group=age_group, district=district)
        session.add(sf)
    await session.commit()


async def get_search_filters(session: AsyncSession, user_id: int) -> SearchFilters | None:
    result = await session.execute(select(SearchFilters).where(SearchFilters.user_id == user_id))
    return result.scalar_one_or_none()


async def get_listing_page(
    session: AsyncSession,
    category: str | None,
    age_group: str | None,
    district: str | None,
    offset: int,
    limit: int = 1,
    exclude_user_id: int | None = None,
):
    q = select(Listing).where(Listing.status == "open").order_by(Listing.created_at.desc())
    q = await apply_listing_visibility_filters(q, exclude_user_id)
    if exclude_user_id is not None:
        q = q.where(Listing.user_id != exclude_user_id)
    if category and category != "all":
        q = q.where(Listing.category == category)
    if age_group and age_group != "any":
        q = q.where(Listing.age_group == age_group)
    if district and district != "any":
        # If user selected a specific district, show listings either for that
        # district or with "any"/no district (видны всем).
        q = q.where(
            or_(
                Listing.district == district,
                Listing.district.is_(None),
                Listing.district == "any",
            )
        )
    q = q.offset(offset).limit(limit)
    result = await session.execute(q)
    return result.scalars().all()


async def get_listing_with_owner(session: AsyncSession, listing_id: int):
    result = await session.execute(
        select(Listing, User).join(User, Listing.user_id == User.id).where(Listing.id == listing_id)
    )
    row = result.one_or_none()
    if row is None:
        return None
    return row
