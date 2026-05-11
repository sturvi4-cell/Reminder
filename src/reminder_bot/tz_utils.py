from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

BAKU = ZoneInfo("Asia/Baku")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_baku() -> datetime:
    return datetime.now(BAKU)


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BAKU)
    return dt.astimezone(timezone.utc)


def to_baku(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BAKU)


def iso(dt: datetime) -> str:
    return dt.isoformat()


def parse_iso(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def fmt_baku(dt: datetime) -> str:
    return to_baku(dt).strftime("%Y-%m-%d %H:%M")


WEEKDAYS_RU = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]


def weekday_ru(dt: datetime) -> str:
    return WEEKDAYS_RU[dt.weekday()]
