from math import ceil

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.config import load_config
from bot.models.user import User
from bot.services.listing import get_listing_by_id
from bot.services.user import get_users_acquisition_counts
from bot.services.report import (
    REPORT_REASON_CONTENT,
    REPORT_REASON_HIDE,
    REPORT_REASON_RULES,
    REPORT_STATUS_PENDING,
    block_user_by_report,
    get_report_by_id,
    get_report_reason_counts_for_user,
    is_admin_visible_report,
    list_blocked_users,
    list_reports,
    report_reason_title,
    report_status_title,
    revoke_report,
    unblock_user,
)

router = Router(name="admin")
config = load_config()
PAGE_SIZE = 5


def _is_admin(telegram_id: int | None) -> bool:
    return config.is_admin(telegram_id)


def _admin_menu_markup():
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Жалобы", callback_data="adm:reports"))
    builder.row(InlineKeyboardButton(text="Черный список", callback_data="adm:black:0"))
    builder.row(InlineKeyboardButton(text="Трафик", callback_data="adm:traffic"))
    return builder.as_markup()


def _reports_root_markup():
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Все жалобы", callback_data="adm:r:all:0"))
    builder.row(InlineKeyboardButton(text="Обработанные", callback_data="adm:r:processed:0"))
    builder.row(InlineKeyboardButton(text="Назад", callback_data="adm:menu"))
    return builder.as_markup()


def _format_user(user: User | None) -> str:
    if user is None:
        return "не найден"
    username = f" @{user.username}" if user.username else ""
    return f"{user.first_name or 'Пользователь'}{username} | tg={user.telegram_id} | id={user.id}"


def _pager_row(builder, *, prefix: str, page: int, total: int):
    from aiogram.types import InlineKeyboardButton

    pages = max(1, ceil(total / PAGE_SIZE))
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="<<", callback_data=f"{prefix}:{page - 1}"))
    row.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="adm:none"))
    if page + 1 < pages:
        row.append(InlineKeyboardButton(text=">>", callback_data=f"{prefix}:{page + 1}"))
    builder.row(*row)


async def _render_reports_list(message, session, *, scope: str, page: int):
    reports, total = await list_reports(session, scope, page, PAGE_SIZE)
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    title = "Обработанные жалобы" if scope == "processed" else "Все жалобы"
    if not reports:
        builder.row(InlineKeyboardButton(text="Назад", callback_data="adm:reports"))
        await message.edit_text(f"{title}\n\nСписок пуст.", reply_markup=builder.as_markup())
        return

    lines = [title, ""]
    for report in reports:
        listing = await get_listing_by_id(session, report.listing_id)
        code = listing.code if listing else f"id={report.listing_id}"
        lines.append(
            f"#{report.id} | {report_reason_title(report.reason)} | {report_status_title(report.status)} | заявка {code}"
        )
        builder.row(
            InlineKeyboardButton(
                text=f"Открыть жалобу #{report.id}",
                callback_data=f"adm:rv:{report.id}:{scope}:{page}",
            )
        )
    _pager_row(builder, prefix=f"adm:r:{scope}", page=page, total=total)
    builder.row(InlineKeyboardButton(text="Назад", callback_data="adm:reports"))
    await message.edit_text("\n".join(lines), reply_markup=builder.as_markup())


async def _render_report_detail(message, session, *, report_id: int, scope: str, page: int):
    report = await get_report_by_id(session, report_id)
    if report is None or not is_admin_visible_report(report.reason):
        await message.edit_text("Жалоба не найдена.", reply_markup=_reports_root_markup())
        return

    listing = await get_listing_by_id(session, report.listing_id)
    reporter = await session.get(User, report.reporter_user_id)
    target = await session.get(User, report.target_user_id)
    counts = await get_report_reason_counts_for_user(session, report.target_user_id)

    text = (
        f"Жалоба #{report.id}\n\n"
        f"Статус: {report_status_title(report.status)}\n"
        f"Причина: {report_reason_title(report.reason)}\n"
        f"Заявка: {listing.code if listing else report.listing_id}\n"
        f"Автор заявки: {_format_user(target)}\n"
        f"Кто пожаловался: {_format_user(reporter)}\n\n"
        "Жалобы на автора:\n"
        f"- Неприемлемый контент: {counts.get(REPORT_REASON_CONTENT, 0)}\n"
        f"- Не соответствует правилам: {counts.get(REPORT_REASON_RULES, 0)}\n"
        f"- Просто скрыть автора: {counts.get(REPORT_REASON_HIDE, 0)}"
    )

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    if report.status == REPORT_STATUS_PENDING:
        builder.row(
            InlineKeyboardButton(text="Заблокировать автора", callback_data=f"adm:act:block:{report.id}:{scope}:{page}")
        )
        builder.row(
            InlineKeyboardButton(text="Отозвать жалобу", callback_data=f"adm:act:revoke:{report.id}:{scope}:{page}")
        )
    builder.row(InlineKeyboardButton(text="Назад к списку", callback_data=f"adm:r:{scope}:{page}"))
    await message.edit_text(text, reply_markup=builder.as_markup())


async def _render_blacklist(message, session, *, page: int):
    users, total = await list_blocked_users(session, page, PAGE_SIZE)
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    if not users:
        builder.row(InlineKeyboardButton(text="Назад", callback_data="adm:menu"))
        await message.edit_text("Черный список пуст.", reply_markup=builder.as_markup())
        return

    lines = ["Черный список", ""]
    for user in users:
        lines.append(_format_user(user))
        builder.row(InlineKeyboardButton(text=f"Реабилитировать {user.id}", callback_data=f"adm:unblock:{user.id}:{page}"))
    _pager_row(builder, prefix="adm:black", page=page, total=total)
    builder.row(InlineKeyboardButton(text="Назад", callback_data="adm:menu"))
    await message.edit_text("\n".join(lines), reply_markup=builder.as_markup())


@router.message(Command("admin"))
@router.message(F.text == "admin")
async def admin_menu(message: Message):
    if not message.from_user or not _is_admin(message.from_user.id):
        return
    await message.answer("Админка", reply_markup=_admin_menu_markup())


@router.callback_query(F.data == "adm:none")
async def admin_none(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "adm:menu")
async def admin_menu_callback(callback: CallbackQuery):
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await callback.message.edit_text("Админка", reply_markup=_admin_menu_markup())
    await callback.answer()


@router.callback_query(F.data == "adm:reports")
async def admin_reports_root(callback: CallbackQuery):
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await callback.message.edit_text("Жалобы", reply_markup=_reports_root_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("adm:r:"))
async def admin_reports_list(callback: CallbackQuery, session):
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    _, _, scope, page_raw = callback.data.split(":")
    await _render_reports_list(callback.message, session, scope=scope, page=int(page_raw))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:rv:"))
async def admin_report_view(callback: CallbackQuery, session):
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    _, _, report_id_raw, scope, page_raw = callback.data.split(":")
    await _render_report_detail(
        callback.message,
        session,
        report_id=int(report_id_raw),
        scope=scope,
        page=int(page_raw),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:act:"))
async def admin_report_action(callback: CallbackQuery, session):
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    _, _, action, report_id_raw, scope, page_raw = callback.data.split(":")
    report_id = int(report_id_raw)
    page = int(page_raw)
    if action == "block":
        report = await block_user_by_report(session, report_id=report_id, admin_telegram_id=callback.from_user.id)
        if report is None:
            await callback.answer("Жалоба уже обработана.", show_alert=True)
            return
    elif action == "revoke":
        report = await revoke_report(session, report_id=report_id, admin_telegram_id=callback.from_user.id)
        if report is None:
            await callback.answer("Жалоба уже обработана.", show_alert=True)
            return
    await _render_report_detail(callback.message, session, report_id=report_id, scope=scope, page=page)
    await callback.answer("Готово.")


@router.callback_query(F.data.startswith("adm:black:"))
async def admin_blacklist(callback: CallbackQuery, session):
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    page = int(callback.data.split(":")[2])
    await _render_blacklist(callback.message, session, page=page)
    await callback.answer()


@router.callback_query(F.data.startswith("adm:unblock:"))
async def admin_unblock(callback: CallbackQuery, session):
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    _, _, user_id_raw, page_raw = callback.data.split(":")
    ok = await unblock_user(session, user_id=int(user_id_raw))
    if not ok:
        await callback.answer("Пользователь уже разблокирован.", show_alert=True)
        return
    await _render_blacklist(callback.message, session, page=int(page_raw))
    await callback.answer("Пользователь реабилитирован.")


@router.callback_query(F.data == "adm:traffic")
async def admin_traffic(callback: CallbackQuery, session):
    if not callback.from_user or not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    counts = await get_users_acquisition_counts(session)
    total = counts["referral"] + counts["instagram"] + counts["other"]
    text = (
        "Источники пользователей\n\n"
        f"Всего пользователей: {total}\n"
        f"По рефералкам: {counts['referral']}\n"
        f"По спецссылке Instagram: {counts['instagram']}\n"
        f"Другим путем: {counts['other']}"
    )
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Назад", callback_data="adm:menu"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()
