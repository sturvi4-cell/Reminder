from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from .. import repo
from ..db import session_scope
from ..keyboards import list_item_kb
from ..scheduler import ReminderScheduler
from ..tz_utils import fmt_baku, parse_iso

router = Router(name="commands")

HELP_TEXT = (
    "<b>Reminder Bot</b>\n\n"
    "Пиши свободным текстом, когда тебе напомнить. Примеры:\n"
    "• <code>сегодня в 18:00 позвонить маме</code>\n"
    "• <code>завтра в 9 утра планёрка</code>\n"
    "• <code>через 30 минут проверить духовку</code>\n"
    "• <code>каждый день в 22:00 принять таблетку</code>\n"
    "• <code>каждый понедельник в 9 утра тренировка</code>\n"
    "• <code>каждый будний день в 8:30 зарядка</code>\n\n"
    "<b>Команды:</b>\n"
    "/list — мои активные напоминания\n"
    "/cancel <id> — удалить по ID\n"
    "/help — эта справка\n\n"
    "Когда напоминание сработает, нажми <b>Принято</b> или <b>Отложить</b>. "
    "Иначе оно повторится через 10 минут."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    async with session_scope() as session:
        await repo.upsert_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            chat_id=message.chat.id,
        )
    await message.answer("Привет! Ты зарегистрирован. " + HELP_TEXT)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("list"))
async def cmd_list(message: Message) -> None:
    async with session_scope() as session:
        items = await repo.list_active(session, user_id=message.from_user.id, limit=20)

    if not items:
        await message.answer("Активных напоминаний нет.")
        return

    await message.answer(f"Активных напоминаний: <b>{len(items)}</b>")
    for r in items:
        if r.kind == "once" and r.once_at_utc:
            when = fmt_baku(parse_iso(r.once_at_utc))
            line = f"#{r.id} • {_esc(r.title)}\n📅 разово, {when} (Баку)"
        else:
            line = f"#{r.id} • {_esc(r.title)}\n🔁 cron: <code>{_esc(r.cron_expr or '')}</code>"
        await message.answer(line, reply_markup=list_item_kb(r.id))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, scheduler: ReminderScheduler) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer("Использование: <code>/cancel &lt;id&gt;</code> (ID из /list)")
        return
    rid = int(parts[1].strip())
    async with session_scope() as session:
        ok = await repo.deactivate_reminder(session, rid, owner_id=message.from_user.id)
    if ok:
        await scheduler.unschedule(rid)
        await message.answer(f"Удалено напоминание #{rid}")
    else:
        await message.answer(f"Напоминание #{rid} не найдено или уже неактивно.")


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
