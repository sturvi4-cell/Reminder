from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    registered_at: Mapped[str] = mapped_column(String(40), nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # 'once' | 'recurring'
    once_at_utc: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    cron_expr: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("idx_reminders_user_active", "user_id", "active"),)


class PendingNotification(Base):
    __tablename__ = "pending_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reminder_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reminders.id", ondelete="CASCADE"), nullable=False
    )
    fired_at_utc: Mapped[str] = mapped_column(String(40), nullable=False)
    next_remind_utc: Mapped[str] = mapped_column(String(40), nullable=False)
    last_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    acknowledged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ack_at_utc: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    repeat_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (Index("idx_pending_unacked", "acknowledged", "next_remind_utc"),)
