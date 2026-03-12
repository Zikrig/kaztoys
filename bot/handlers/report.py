from aiogram import F, Router, Bot
from aiogram.types import CallbackQuery

from bot.config import load_config
from bot.keyboards.report import report_reason_keyboard
from bot.services.listing import get_listing_by_id
from bot.services.report import (
    REPORT_REASON_CONTENT,
    REPORT_REASON_HIDE,
    REPORT_REASON_RULES,
    create_report,
    get_report_by_id,
    is_admin_visible_report,
    report_reason_title,
)
from bot.services.user import get_user_by_telegram_id
from bot.models.user import User

router = Router(name="report")
config = load_config()


def _admin_notification_text(report_id: int, reason: str, listing_code: str, reporter_name: str, target_name: str) -> str:
    return (
        "Новая жалоба.\n\n"
        f"Жалоба #{report_id}\n"
        f"Причина: {report_reason_title(reason)}\n"
        f"Заявка: {listing_code}\n"
        f"Кто пожаловался: {reporter_name}\n"
        f"На кого: {target_name}"
    )


async def _notify_admins(bot: Bot, session, report_id: int) -> None:
    report = await get_report_by_id(session, report_id)
    if report is None or not is_admin_visible_report(report.reason):
        return
    listing = await get_listing_by_id(session, report.listing_id)
    reporter = await session.get(User, report.reporter_user_id)
    target = await session.get(User, report.target_user_id)

    reporter_name = reporter.first_name or reporter.username or str(report.reporter_user_id) if reporter else str(report.reporter_user_id)
    target_name = target.first_name or target.username or str(report.target_user_id) if target else str(report.target_user_id)
    listing_code = listing.code if listing else str(report.listing_id)

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Открыть жалобу", callback_data=f"adm:rv:{report.id}:all:0"))
    text = _admin_notification_text(report.id, report.reason, listing_code, reporter_name, target_name)
    for admin_id in config.admin_ids_set():
        try:
            await bot.send_message(admin_id, text, reply_markup=builder.as_markup())
        except Exception:
            pass


@router.callback_query(F.data.startswith("rep:start:"))
async def report_start(callback: CallbackQuery, session):
    listing_id = int(callback.data.split(":", 2)[2])
    if not callback.from_user:
        await callback.answer()
        return
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    listing = await get_listing_by_id(session, listing_id)
    if not user or not listing:
        await callback.answer("Заявка недоступна.", show_alert=True)
        return
    if listing.user_id == user.id:
        await callback.answer("Нельзя пожаловаться на свою заявку.", show_alert=True)
        return
    await callback.message.answer(
        "Укажите причину жалобы:",
        reply_markup=report_reason_keyboard(listing_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rep:rsn:"))
async def report_reason_chosen(callback: CallbackQuery, session, bot: Bot):
    _, _, listing_id_raw, reason = callback.data.split(":", 3)
    listing_id = int(listing_id_raw)
    if not callback.from_user:
        await callback.answer()
        return
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    listing = await get_listing_by_id(session, listing_id)
    if not user or not listing:
        await callback.answer("Заявка недоступна.", show_alert=True)
        return
    if listing.user_id == user.id:
        await callback.answer("Нельзя пожаловаться на свою заявку.", show_alert=True)
        return
    report, created = await create_report(
        session,
        reporter_user_id=user.id,
        listing=listing,
        reason=reason,
    )
    if created:
        await _notify_admins(bot, session, report.id)

    if not created:
        await callback.answer("Такая жалоба уже отправлена и ждет решения.", show_alert=True)
        return

    if reason == REPORT_REASON_CONTENT:
        text = "Жалоба отправлена. До решения админа заявки этого автора вам больше не показываются."
    elif reason == REPORT_REASON_RULES:
        text = "Жалоба отправлена. Эта заявка заморожена до решения админа."
    elif reason == REPORT_REASON_HIDE:
        text = "Автор скрыт для вас."
    else:
        text = "Жалоба отправлена."
    await callback.message.answer(text)
    await callback.answer("Жалоба отправлена.")


