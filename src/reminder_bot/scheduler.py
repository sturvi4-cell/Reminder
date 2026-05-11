from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramBadRequest
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from . import repo
from .config import Settings
from .db import session_scope, sync_sqlite_url
from .keyboards import notification_kb
from .models import Reminder, User
from .tz_utils import fmt_baku, now_utc, parse_iso, to_baku

log = logging.getLogger(__name__)

_SCHEDULER: "ReminderScheduler | None" = None


def get_scheduler() -> "ReminderScheduler":
    if _SCHEDULER is None:
        raise RuntimeError("Scheduler not initialized")
    return _SCHEDULER


# Module-level callbacks for APScheduler (must be importable for jobstore persistence).
async def _job_fire(reminder_id: int) -> None:
    await get_scheduler().fire(reminder_id, missed=False)


async def _job_snooze_fire(reminder_id: int) -> None:
    await get_scheduler().fire(reminder_id, missed=False, snoozed=True)


class ReminderScheduler:
    def __init__(self, bot: Bot, settings: Settings) -> None:
        self.bot = bot
        self.settings = settings
        jobstore = SQLAlchemyJobStore(url=sync_sqlite_url(settings.DB_PATH))
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": jobstore},
            timezone=timezone.utc,
            job_defaults={"misfire_grace_time": 3600, "coalesce": True},
        )

    async def start(self) -> None:
        global _SCHEDULER
        _SCHEDULER = self
        self.scheduler.start()
        # Periodic repeat-loop for unacknowledged pending notifications.
        self.scheduler.add_job(
            _repeat_tick,
            IntervalTrigger(minutes=1),
            id="repeat_tick",
            replace_existing=True,
        )
        await self.catchup_missed()

    async def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)

    # ------- scheduling API -------

    async def schedule_reminder(self, reminder: Reminder) -> None:
        job_id = f"rem:{reminder.id}"
        if reminder.kind == "once":
            if not reminder.once_at_utc:
                return
            run_at = parse_iso(reminder.once_at_utc)
            self.scheduler.add_job(
                _job_fire,
                DateTrigger(run_date=run_at),
                args=[reminder.id],
                id=job_id,
                replace_existing=True,
            )
        elif reminder.kind == "recurring":
            if not reminder.cron_expr:
                return
            trigger = CronTrigger.from_crontab(reminder.cron_expr, timezone=timezone.utc)
            self.scheduler.add_job(
                _job_fire,
                trigger,
                args=[reminder.id],
                id=job_id,
                replace_existing=True,
            )

    async def unschedule(self, reminder_id: int) -> None:
        try:
            self.scheduler.remove_job(f"rem:{reminder_id}")
        except Exception:
            pass

    # ------- firing -------

    async def fire(self, reminder_id: int, *, missed: bool = False, snoozed: bool = False) -> None:
        async with session_scope() as session:
            reminder = await repo.get_reminder(session, reminder_id)
            if reminder is None or not reminder.active:
                return
            user = await session.get(User, reminder.user_id)
            if user is None or not user.is_active:
                return

            next_remind = now_utc() + timedelta(minutes=self.settings.REPEAT_INTERVAL_MIN)
            pending = await repo.create_pending(session, reminder.id, next_remind)
            text = _format_notification(reminder.title, missed=missed, snoozed=snoozed)
            chat_id = user.chat_id

        message_id = await self._send_notification(reminder.user_id, chat_id, text, pending.id)
        if message_id is not None:
            async with session_scope() as session:
                await repo.set_pending_message_id(session, pending.id, message_id)

        # If once-reminder fired, deactivate it (recurring stays active).
        if reminder.kind == "once":
            async with session_scope() as session:
                await repo.deactivate_reminder(session, reminder.id, reminder.user_id)

    async def _send_notification(self, user_id: int, chat_id: int, text: str, pending_id: int) -> Optional[int]:
        try:
            msg = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=notification_kb(pending_id),
            )
            return msg.message_id
        except TelegramRetryAfter as exc:
            log.warning("Flood wait %ds for user %s", exc.retry_after, user_id)
            return None
        except TelegramForbiddenError:
            log.warning("User %s blocked the bot — deactivating", user_id)
            async with session_scope() as session:
                await repo.deactivate_user(session, user_id)
            return None
        except TelegramBadRequest as exc:
            log.warning("Bad request sending to %s: %s", user_id, exc)
            return None

    async def acknowledge(self, pending_id: int) -> bool:
        async with session_scope() as session:
            return await repo.acknowledge_pending(session, pending_id)

    async def snooze(self, pending_id: int, minutes: int) -> Optional[int]:
        async with session_scope() as session:
            pending = await repo.get_pending(session, pending_id)
            if pending is None or pending.acknowledged:
                return None
            await repo.acknowledge_pending(session, pending_id)
            reminder_id = pending.reminder_id

        run_at = now_utc() + timedelta(minutes=minutes)
        self.scheduler.add_job(
            _job_snooze_fire,
            DateTrigger(run_date=run_at),
            args=[reminder_id],
            id=f"snz:{pending_id}:{int(run_at.timestamp())}",
            replace_existing=True,
        )
        return reminder_id

    async def catchup_missed(self) -> None:
        """At startup, fire any once-reminders whose time already passed."""
        async with session_scope() as session:
            due = await repo.list_due_once(session)
            ids = [r.id for r in due]
        for rid in ids:
            log.info("Catchup: firing missed once-reminder id=%s", rid)
            try:
                await self.fire(rid, missed=True)
            except Exception:
                log.exception("Catchup fire failed for id=%s", rid)


# Module-level periodic callback (must be importable for jobstore).
async def _repeat_tick() -> None:
    sched = get_scheduler()
    async with session_scope() as session:
        due = await repo.list_due_unacked(session)
        items = [(p.id, p.reminder_id) for p in due]

    if not items:
        return

    for pending_id, reminder_id in items:
        async with session_scope() as session:
            reminder = await repo.get_reminder(session, reminder_id)
            if reminder is None or not reminder.active:
                continue
            user = await session.get(User, reminder.user_id)
            if user is None or not user.is_active:
                continue
            chat_id = user.chat_id
            text = _format_notification(reminder.title, repeat=True)

        try:
            msg = await sched.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=notification_kb(pending_id),
            )
            next_remind = now_utc() + timedelta(minutes=sched.settings.REPEAT_INTERVAL_MIN)
            async with session_scope() as session:
                await repo.bump_pending(session, pending_id, msg.message_id, next_remind)
        except TelegramForbiddenError:
            async with session_scope() as session:
                await repo.deactivate_user(session, reminder.user_id)
        except TelegramRetryAfter as exc:
            log.warning("Flood wait %ds during repeat", exc.retry_after)
        except Exception:
            log.exception("Repeat send failed for pending=%s", pending_id)


def _format_notification(title: str, *, missed: bool = False, snoozed: bool = False, repeat: bool = False) -> str:
    prefix = "🔁 Повтор: " if repeat else ("⏱ Отложено: " if snoozed else ("⚠️ Пропущено: " if missed else "🔔 "))
    return f"{prefix}<b>{_html_escape(title)}</b>"


def _html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
