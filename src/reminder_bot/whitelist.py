from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from . import repo
from .config import Settings
from .db import session_scope

log = logging.getLogger(__name__)


WELCOME_AFTER_REGISTRATION = (
    "✅ Доступ открыт. Теперь можешь писать напоминания свободным текстом.\n\n"
    "Примеры:\n"
    "• <code>сегодня в 18:00 позвонить маме</code>\n"
    "• <code>завтра в 9 утра планёрка</code>\n"
    "• <code>каждый день в 22:00 принять таблетку</code>\n"
    "• <code>sabah saat 15:00 ana zəng et</code>\n\n"
    "Команды: /help /list /cancel"
)

ASK_SECRET = (
    "🔒 Доступ закрыт. Отправь секретное слово одним сообщением, чтобы зарегистрироваться."
)


async def _is_registered(telegram_id: int) -> bool:
    async with session_scope() as session:
        user = await repo.get_user(session, telegram_id)
        return user is not None and user.is_active == 1


class AuthMiddleware(BaseMiddleware):
    """Gate every update: registered users pass through; others can register
    by sending the REGISTRATION_SECRET in a plain message. Everything else
    from unregistered users is silently rejected with a hint."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None:
            return None

        if await _is_registered(user.id):
            return await handler(event, data)

        # Unregistered: only Message can register; callback queries are rejected.
        if isinstance(event, CallbackQuery):
            await event.answer("Сначала зарегистрируйся: отправь секретное слово в чат.", show_alert=True)
            return None

        if not isinstance(event, Message):
            return None

        text = (event.text or "").strip()
        if text == self.settings.REGISTRATION_SECRET:
            async with session_scope() as session:
                await repo.upsert_user(
                    session,
                    telegram_id=user.id,
                    username=user.username,
                    chat_id=event.chat.id,
                )
            log.info("Registered user id=%s username=%s", user.id, user.username)
            await event.answer(WELCOME_AFTER_REGISTRATION)
            return None

        await event.answer(ASK_SECRET)
        return None


# Backwards-compatible alias (bot.py imports WhitelistMiddleware).
WhitelistMiddleware = AuthMiddleware
