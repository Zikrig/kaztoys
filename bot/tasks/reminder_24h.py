"""Отправка напоминания «Помните?» через 24 часа после создания мэтча."""
from datetime import datetime, timezone
import logging

from aiogram import Bot

from bot.models.base import get_async_session_maker
from bot.keyboards.report import report_button_row
from bot.services.match import get_matches_for_reminder, mark_reminder_sent
from bot.services.listing import get_listing_by_id
from bot.services.response import get_response_by_id

log = logging.getLogger("bot.tasks.reminder_24h")

REMINDER_TEXT = (
    "Помните? Подтвердите, что обмен состоялся, или отмените сделку.\n\n"
    "Ваша заявка. Код {listing_code}. {listing_desc}\n\n"
    "Отклик. Код {response_code}. {response_desc}\n\n"
    "Контакт второй стороны: {contact}"
)


async def run_reminder_cycle(bot: Bot) -> None:
    session_factory = get_async_session_maker()
    async with session_factory() as session:
        matches = await get_matches_for_reminder(session, after_hours=24.0)
        for match in matches:
            try:
                listing = await get_listing_by_id(session, match.listing_id)
                resp = await get_response_by_id(session, match.response_id)
                if not listing or not resp:
                    continue
                from bot.models.user import User
                owner = await session.get(User, match.listing_owner_id)
                respondent = await session.get(User, match.response_owner_id)
                contact_owner = (owner.first_name or "Пользователь") + (f" @{owner.username}" if owner and owner.username else "")
                contact_resp = (respondent.first_name or "Пользователь") + (f" @{respondent.username}" if respondent and respondent.username else "")
                text = REMINDER_TEXT.format(
                    listing_code=listing.code,
                    listing_desc=listing.description,
                    response_code=resp.code,
                    response_desc=resp.description,
                    contact="",  # will set per recipient
                )
                from aiogram.types import InlineKeyboardButton
                from aiogram.utils.keyboard import InlineKeyboardBuilder
                builder = InlineKeyboardBuilder()
                builder.row(
                    InlineKeyboardButton(text="Подтвердить сделку", callback_data=f"match_confirm:{match.id}"),
                    InlineKeyboardButton(text="Сделка не состоялась", callback_data=f"match_cancel:{match.id}"),
                )
                report_builder = InlineKeyboardBuilder()
                report_builder.row(*report_button_row(listing_id=listing.id))
                text_owner = REMINDER_TEXT.format(
                    listing_code=listing.code,
                    listing_desc=listing.description,
                    response_code=resp.code,
                    response_desc=resp.description,
                    contact=contact_resp,
                )
                text_resp = REMINDER_TEXT.format(
                    listing_code=listing.code,
                    listing_desc=listing.description,
                    response_code=resp.code,
                    response_desc=resp.description,
                    contact=contact_owner,
                )
                await bot.send_photo(
                    owner.telegram_id,
                    photo=listing.photo_file_id or "",
                    caption=text_owner,
                    reply_markup=report_builder.as_markup(),
                )
                await bot.send_photo(owner.telegram_id, photo=resp.photo_file_id or "")
                await bot.send_message(owner.telegram_id, "Подтвердите сделку или отмените:", reply_markup=builder.as_markup())
                await bot.send_photo(
                    respondent.telegram_id,
                    photo=listing.photo_file_id or "",
                    caption=text_resp,
                    reply_markup=report_builder.as_markup(),
                )
                await bot.send_photo(respondent.telegram_id, photo=resp.photo_file_id or "")
                await bot.send_message(respondent.telegram_id, "Подтвердите сделку или отмените:", reply_markup=builder.as_markup())
                await mark_reminder_sent(session, match.id)
            except Exception as e:
                log.exception("Reminder send failed for match %s: %s", match.id, e)
