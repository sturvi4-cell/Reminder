from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import PendingNotification, Reminder, User
from .tz_utils import iso, now_utc


# -------- users --------

async def upsert_user(session: AsyncSession, telegram_id: int, username: Optional[str], chat_id: int) -> User:
    user = await session.get(User, telegram_id)
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=(username or "").lstrip("@") or None,
            chat_id=chat_id,
            registered_at=iso(now_utc()),
            is_active=1,
        )
        session.add(user)
        await session.flush()
    else:
        user.username = (username or "").lstrip("@") or None
        user.chat_id = chat_id
        user.is_active = 1
    return user


async def deactivate_user(session: AsyncSession, telegram_id: int) -> None:
    await session.execute(
        update(User).where(User.telegram_id == telegram_id).values(is_active=0)
    )


# -------- reminders --------

async def create_reminder(
    session: AsyncSession,
    user_id: int,
    title: str,
    kind: str,
    once_at_utc: Optional[datetime],
    cron_expr: Optional[str],
    raw_text: Optional[str],
) -> Reminder:
    reminder = Reminder(
        user_id=user_id,
        title=title,
        kind=kind,
        once_at_utc=iso(once_at_utc) if once_at_utc else None,
        cron_expr=cron_expr,
        active=1,
        created_at=iso(now_utc()),
        raw_text=raw_text,
    )
    session.add(reminder)
    await session.flush()
    return reminder


async def get_reminder(session: AsyncSession, reminder_id: int) -> Optional[Reminder]:
    return await session.get(Reminder, reminder_id)


async def list_active(session: AsyncSession, user_id: int, limit: int = 20) -> Sequence[Reminder]:
    res = await session.execute(
        select(Reminder)
        .where(Reminder.user_id == user_id, Reminder.active == 1)
        .order_by(Reminder.id.desc())
        .limit(limit)
    )
    return res.scalars().all()


async def deactivate_reminder(session: AsyncSession, reminder_id: int, owner_id: int) -> bool:
    res = await session.execute(
        update(Reminder)
        .where(Reminder.id == reminder_id, Reminder.user_id == owner_id, Reminder.active == 1)
        .values(active=0)
    )
    return res.rowcount > 0


async def list_due_once(session: AsyncSession, now: Optional[datetime] = None) -> Sequence[Reminder]:
    """Once-reminders that should have already fired but didn't (used at startup)."""
    now = now or now_utc()
    res = await session.execute(
        select(Reminder).where(
            Reminder.active == 1,
            Reminder.kind == "once",
            Reminder.once_at_utc.is_not(None),
            Reminder.once_at_utc <= iso(now),
        )
    )
    return res.scalars().all()


async def list_all_active(session: AsyncSession) -> Sequence[Reminder]:
    res = await session.execute(select(Reminder).where(Reminder.active == 1))
    return res.scalars().all()


# -------- pending notifications --------

async def create_pending(
    session: AsyncSession,
    reminder_id: int,
    next_remind_utc: datetime,
) -> PendingNotification:
    now = now_utc()
    pending = PendingNotification(
        reminder_id=reminder_id,
        fired_at_utc=iso(now),
        next_remind_utc=iso(next_remind_utc),
        acknowledged=0,
        repeat_count=0,
    )
    session.add(pending)
    await session.flush()
    return pending


async def get_pending(session: AsyncSession, pending_id: int) -> Optional[PendingNotification]:
    return await session.get(PendingNotification, pending_id)


async def set_pending_message_id(session: AsyncSession, pending_id: int, message_id: int) -> None:
    await session.execute(
        update(PendingNotification)
        .where(PendingNotification.id == pending_id)
        .values(last_message_id=message_id)
    )


async def list_due_unacked(session: AsyncSession, now: Optional[datetime] = None) -> Sequence[PendingNotification]:
    now = now or now_utc()
    res = await session.execute(
        select(PendingNotification).where(
            PendingNotification.acknowledged == 0,
            PendingNotification.next_remind_utc <= iso(now),
        )
    )
    return res.scalars().all()


async def bump_pending(session: AsyncSession, pending_id: int, message_id: int, next_remind_utc: datetime) -> None:
    await session.execute(
        update(PendingNotification)
        .where(PendingNotification.id == pending_id)
        .values(
            last_message_id=message_id,
            next_remind_utc=iso(next_remind_utc),
            repeat_count=PendingNotification.repeat_count + 1,
        )
    )


async def acknowledge_pending(session: AsyncSession, pending_id: int) -> bool:
    res = await session.execute(
        update(PendingNotification)
        .where(PendingNotification.id == pending_id, PendingNotification.acknowledged == 0)
        .values(acknowledged=1, ack_at_utc=iso(now_utc()))
    )
    return res.rowcount > 0
