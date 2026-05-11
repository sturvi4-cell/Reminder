from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from .. import repo
from ..db import session_scope
from ..scheduler import ReminderScheduler

router = Router(name="callbacks")
log = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("ack:"))
async def on_ack(cq: CallbackQuery, scheduler: ReminderScheduler) -> None:
    pid = int(cq.data.split(":")[1])
    ok = await scheduler.acknowledge(pid)
    await _strip_kb(cq)
    await cq.answer("Принято" if ok else "Уже подтверждено")


@router.callback_query(F.data.startswith("snz:"))
async def on_snooze(cq: CallbackQuery, scheduler: ReminderScheduler) -> None:
    _, pid_s, mins_s = cq.data.split(":")
    pid, mins = int(pid_s), int(mins_s)
    rid = await scheduler.snooze(pid, mins)
    await _strip_kb(cq)
    if rid is None:
        await cq.answer("Уже подтверждено")
    else:
        await cq.answer(f"Отложено на {mins} мин")


@router.callback_query(F.data.startswith("del:"))
async def on_delete(cq: CallbackQuery, scheduler: ReminderScheduler) -> None:
    rid = int(cq.data.split(":")[1])
    async with session_scope() as session:
        ok = await repo.deactivate_reminder(session, rid, owner_id=cq.from_user.id)
    if ok:
        await scheduler.unschedule(rid)
        await _strip_kb(cq)
        await cq.answer("Удалено")
        try:
            await cq.message.edit_text((cq.message.text or "") + "\n\n🗑 Удалено")
        except TelegramBadRequest:
            pass
    else:
        await cq.answer("Уже удалено", show_alert=False)


async def _strip_kb(cq: CallbackQuery) -> None:
    try:
        await cq.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
