from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from . import repo
from .config import Settings
from .db import init_db, session_scope
from .handlers import callbacks as h_callbacks
from .handlers import commands as h_commands
from .handlers import text as h_text
from .logging_setup import setup_logging
from .scheduler import ReminderScheduler
from .whitelist import WhitelistMiddleware

log = logging.getLogger(__name__)


async def _reschedule_all(scheduler: ReminderScheduler) -> None:
    async with session_scope() as session:
        reminders = await repo.list_all_active(session)
        items = list(reminders)
    for r in items:
        try:
            await scheduler.schedule_reminder(r)
        except Exception:
            log.exception("Failed to reschedule reminder id=%s", r.id)


async def run() -> None:
    settings = Settings()
    setup_logging(settings.LOG_LEVEL)
    await init_db(settings.DB_PATH)

    bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    middleware = WhitelistMiddleware(settings)
    dp.message.middleware(middleware)
    dp.callback_query.middleware(middleware)

    scheduler = ReminderScheduler(bot, settings)
    await scheduler.start()
    await _reschedule_all(scheduler)

    dp["scheduler"] = scheduler
    dp["settings"] = settings

    dp.include_router(h_commands.router)
    dp.include_router(h_callbacks.router)
    dp.include_router(h_text.router)

    log.info("Bot started. Model=%s TZ=%s", settings.OPENROUTER_MODEL, settings.TIMEZONE)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await scheduler.shutdown()
        await bot.session.close()


def main() -> None:
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
