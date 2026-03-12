from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.hidden_author import HiddenAuthor
from bot.models.listing import Listing
from bot.models.report import Report
from bot.models.user import User

REPORT_REASON_CONTENT = "content"
REPORT_REASON_RULES = "rules"
REPORT_REASON_HIDE = "hide"

REPORT_STATUS_PENDING = "pending"
REPORT_STATUS_BLOCKED = "blocked"
REPORT_STATUS_REVOKED = "revoked"

HIDDEN_REASON_PERSONAL = "personal"
HIDDEN_REASON_PENDING_CONTENT = "pending_content"

REPORT_REASON_TITLES = {
    REPORT_REASON_CONTENT: "Неприемлемый контент",
    REPORT_REASON_RULES: "Не соответствует правилам",
    REPORT_REASON_HIDE: "Просто скрыть автора",
}

ADMIN_VISIBLE_REPORT_REASONS = {REPORT_REASON_CONTENT, REPORT_REASON_RULES}

REPORT_STATUS_TITLES = {
    REPORT_STATUS_PENDING: "Ожидает решения",
    REPORT_STATUS_BLOCKED: "Автор заблокирован",
    REPORT_STATUS_REVOKED: "Жалоба отозвана",
}


def report_reason_title(reason: str) -> str:
    return REPORT_REASON_TITLES.get(reason, reason)


def report_status_title(status: str) -> str:
    return REPORT_STATUS_TITLES.get(status, status)


def is_admin_visible_report(reason: str) -> bool:
    return reason in ADMIN_VISIBLE_REPORT_REASONS


async def is_user_blocked(session: AsyncSession, telegram_id: int) -> bool:
    result = await session.execute(select(User.is_blocked).where(User.telegram_id == telegram_id))
    value = result.scalar_one_or_none()
    return bool(value)


async def ensure_hidden_author(
    session: AsyncSession,
    *,
    user_id: int,
    hidden_user_id: int,
    reason: str,
    report_id: int | None = None,
) -> HiddenAuthor:
    result = await session.execute(
        select(HiddenAuthor).where(
            HiddenAuthor.user_id == user_id,
            HiddenAuthor.hidden_user_id == hidden_user_id,
            HiddenAuthor.reason == reason,
        )
    )
    hidden = result.scalar_one_or_none()
    if hidden is not None:
        if report_id is not None and hidden.report_id is None:
            hidden.report_id = report_id
        return hidden
    hidden = HiddenAuthor(
        user_id=user_id,
        hidden_user_id=hidden_user_id,
        reason=reason,
        report_id=report_id,
    )
    session.add(hidden)
    await session.flush()
    return hidden


async def remove_hidden_author_by_report(session: AsyncSession, report_id: int) -> None:
    result = await session.execute(select(HiddenAuthor).where(HiddenAuthor.report_id == report_id))
    for hidden in result.scalars().all():
        await session.delete(hidden)


async def apply_listing_visibility_filters(query, viewer_user_id: int | None):
    blocked_users = select(User.id).where(User.is_blocked.is_(True))
    query = query.where(~Listing.user_id.in_(blocked_users))
    if viewer_user_id is not None:
        hidden_authors = select(HiddenAuthor.hidden_user_id).where(HiddenAuthor.user_id == viewer_user_id)
        query = query.where(~Listing.user_id.in_(hidden_authors))
    return query


async def can_view_listing(session: AsyncSession, *, viewer_user_id: int | None, author_user_id: int) -> bool:
    author = await session.get(User, author_user_id)
    if not author or author.is_blocked:
        return False
    if viewer_user_id is None:
        return True
    result = await session.execute(
        select(HiddenAuthor.id).where(
            HiddenAuthor.user_id == viewer_user_id,
            HiddenAuthor.hidden_user_id == author_user_id,
        )
    )
    return result.scalar_one_or_none() is None


async def create_report(
    session: AsyncSession,
    *,
    reporter_user_id: int,
    listing: Listing,
    reason: str,
) -> tuple[Report, bool]:
    result = await session.execute(
        select(Report).where(
            Report.reporter_user_id == reporter_user_id,
            Report.listing_id == listing.id,
            Report.reason == reason,
            Report.status == REPORT_STATUS_PENDING,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing, False

    report = Report(
        reporter_user_id=reporter_user_id,
        target_user_id=listing.user_id,
        listing_id=listing.id,
        reason=reason,
        status=REPORT_STATUS_PENDING,
    )
    session.add(report)
    await session.flush()

    if reason == REPORT_REASON_CONTENT:
        await ensure_hidden_author(
            session,
            user_id=reporter_user_id,
            hidden_user_id=listing.user_id,
            reason=HIDDEN_REASON_PENDING_CONTENT,
            report_id=report.id,
        )
    elif reason == REPORT_REASON_HIDE:
        await ensure_hidden_author(
            session,
            user_id=reporter_user_id,
            hidden_user_id=listing.user_id,
            reason=HIDDEN_REASON_PERSONAL,
            report_id=report.id,
        )
    elif reason == REPORT_REASON_RULES and listing.status == "open":
        listing.status = "frozen"

    await session.commit()
    await session.refresh(report)
    return report, True


async def get_report_by_id(session: AsyncSession, report_id: int) -> Report | None:
    result = await session.execute(select(Report).where(Report.id == report_id))
    return result.scalar_one_or_none()


async def list_reports(session: AsyncSession, scope: str, page: int, page_size: int):
    base = select(Report).where(Report.reason.in_(ADMIN_VISIBLE_REPORT_REASONS))
    count_stmt = select(func.count(Report.id)).where(Report.reason.in_(ADMIN_VISIBLE_REPORT_REASONS))
    if scope == "processed":
        base = base.where(Report.status != REPORT_STATUS_PENDING)
        count_stmt = count_stmt.where(Report.status != REPORT_STATUS_PENDING)
    base = base.order_by(Report.created_at.desc(), Report.id.desc()).offset(page * page_size).limit(page_size)
    reports = (await session.execute(base)).scalars().all()
    total = (await session.execute(count_stmt)).scalar_one() or 0
    return reports, int(total)


async def get_report_reason_counts_for_user(session: AsyncSession, user_id: int) -> dict[str, int]:
    result = await session.execute(
        select(Report.reason, func.count(Report.id)).where(Report.target_user_id == user_id).group_by(Report.reason)
    )
    counts = defaultdict(int)
    for reason, count in result.all():
        counts[reason] = int(count)
    return dict(counts)


async def revoke_report(session: AsyncSession, *, report_id: int, admin_telegram_id: int) -> Report | None:
    report = await get_report_by_id(session, report_id)
    if report is None or report.status != REPORT_STATUS_PENDING or not is_admin_visible_report(report.reason):
        return None
    listing = await session.get(Listing, report.listing_id)

    if report.reason in {REPORT_REASON_CONTENT, REPORT_REASON_HIDE}:
        hidden_reason = HIDDEN_REASON_PENDING_CONTENT if report.reason == REPORT_REASON_CONTENT else HIDDEN_REASON_PERSONAL
        other_pending_stmt = select(func.count(Report.id)).where(
            Report.reporter_user_id == report.reporter_user_id,
            Report.target_user_id == report.target_user_id,
            Report.reason == report.reason,
            Report.status == REPORT_STATUS_PENDING,
            Report.id != report.id,
        )
        other_pending = (await session.execute(other_pending_stmt)).scalar_one() or 0
        if int(other_pending) == 0:
            hidden_stmt = select(HiddenAuthor).where(
                HiddenAuthor.user_id == report.reporter_user_id,
                HiddenAuthor.hidden_user_id == report.target_user_id,
                HiddenAuthor.reason == hidden_reason,
            )
            hidden_rows = (await session.execute(hidden_stmt)).scalars().all()
            for hidden in hidden_rows:
                await session.delete(hidden)
    if report.reason == REPORT_REASON_RULES and listing is not None and listing.status == "frozen":
        listing.status = "open"

    report.status = REPORT_STATUS_REVOKED
    report.admin_telegram_id = admin_telegram_id
    report.processed_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(report)
    return report


async def block_user_by_report(session: AsyncSession, *, report_id: int, admin_telegram_id: int) -> Report | None:
    report = await get_report_by_id(session, report_id)
    if report is None or report.status != REPORT_STATUS_PENDING or not is_admin_visible_report(report.reason):
        return None
    user = await session.get(User, report.target_user_id)
    if user is None:
        return None

    user.is_blocked = True
    user.blocked_reason = f"report:{report.reason}"
    user.blocked_by_admin_id = admin_telegram_id
    user.blocked_at = datetime.now(timezone.utc)

    report.status = REPORT_STATUS_BLOCKED
    report.admin_telegram_id = admin_telegram_id
    report.processed_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(report)
    return report


async def list_blocked_users(session: AsyncSession, page: int, page_size: int):
    users_stmt = (
        select(User)
        .where(User.is_blocked.is_(True))
        .order_by(User.blocked_at.desc().nullslast(), User.id.desc())
        .offset(page * page_size)
        .limit(page_size)
    )
    total_stmt = select(func.count(User.id)).where(User.is_blocked.is_(True))
    users = (await session.execute(users_stmt)).scalars().all()
    total = (await session.execute(total_stmt)).scalar_one() or 0
    return users, int(total)


async def unblock_user(session: AsyncSession, *, user_id: int) -> bool:
    user = await session.get(User, user_id)
    if user is None or not user.is_blocked:
        return False
    user.is_blocked = False
    user.blocked_reason = None
    user.blocked_by_admin_id = None
    user.blocked_at = None
    await session.commit()
    return True
