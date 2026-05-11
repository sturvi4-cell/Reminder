from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import Message
from apscheduler.triggers.cron import CronTrigger

from .. import repo
from ..config import Settings
from ..db import session_scope
from ..llm import LLMError, parse_user_text
from ..scheduler import ReminderScheduler
from ..tz_utils import fmt_baku, now_utc, parse_iso, to_utc

router = Router(name="text")
log = logging.getLogger(__name__)


@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message, scheduler: ReminderScheduler, settings: Settings) -> None:
    text = (message.text or "").strip()
    if not text:
        return

    # Ensure user exists (in case they bypassed /start somehow).
    async with session_scope() as session:
        await repo.upsert_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            chat_id=message.chat.id,
        )

    try:
        parsed = await parse_user_text(settings, text)
    except LLMError as exc:
        log.warning("LLM error: %s", exc)
        await message.answer("Сервис распознавания временно недоступен. Попробуй ещё раз через минуту.")
        return
    except Exception:
        log.exception("Unexpected parser error")
        await message.answer("Не удалось распознать. Попробуй переформулировать.")
        return

    if parsed.kind == "error":
        await message.answer(f"Не понял: {parsed.reason or 'не распознал время'}. Переформулируй, пожалуйста.")
        return

    if parsed.kind == "once":
        if not parsed.when_iso or not parsed.title:
            await message.answer("Не получилось распознать время или суть. Переформулируй.")
            return
        try:
            when_dt = parse_iso(parsed.when_iso)
        except ValueError:
            await message.answer("Не понял дату. Переформулируй.")
            return
        when_utc = to_utc(when_dt)
        if when_utc <= now_utc():
            await message.answer("Время уже в прошлом. Уточни.")
            return

        async with session_scope() as session:
            reminder = await repo.create_reminder(
                session,
                user_id=message.from_user.id,
                title=parsed.title,
                kind="once",
                once_at_utc=when_utc,
                cron_expr=None,
                raw_text=text,
            )
        await scheduler.schedule_reminder(reminder)
        await message.answer(
            f"✅ Запланировано #{reminder.id}\n"
            f"📌 {_esc(reminder.title)}\n"
            f"📅 {fmt_baku(when_utc)} (Баку)"
        )
        return

    if parsed.kind == "recurring":
        if not parsed.cron or not parsed.title:
            await message.answer("Не получилось распознать расписание или суть. Переформулируй.")
            return
        try:
            CronTrigger.from_crontab(parsed.cron)
        except (ValueError, KeyError):
            await message.answer(f"Некорректное расписание: <code>{_esc(parsed.cron)}</code>. Переформулируй.")
            return

        async with session_scope() as session:
            reminder = await repo.create_reminder(
                session,
                user_id=message.from_user.id,
                title=parsed.title,
                kind="recurring",
                once_at_utc=None,
                cron_expr=parsed.cron,
                raw_text=text,
            )
        await scheduler.schedule_reminder(reminder)
        await message.answer(
            f"✅ Регулярное #{reminder.id}\n"
            f"📌 {_esc(reminder.title)}\n"
            f"🔁 cron: <code>{_esc(parsed.cron)}</code>"
        )


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
