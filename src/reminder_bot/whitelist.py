from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from .config import Settings

log = logging.getLogger(__name__)


def is_allowed(user: User | None, settings: Settings) -> bool:
    if user is None:
        return False
    if settings.WHITELIST_USER_IDS and user.id in settings.WHITELIST_USER_IDS:
        return True
    if settings.WHITELIST_USERNAMES and (user.username or "").lower() in settings.WHITELIST_USERNAMES:
        return True
    return False


class WhitelistMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if not is_allowed(user, self.settings):
            log.warning("Rejected user_id=%s username=%s", getattr(user, "id", None), getattr(user, "username", None))
            if isinstance(event, Message):
                await event.answer("Доступ запрещён. Попросите владельца добавить вас в whitelist.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Доступ запрещён.", show_alert=True)
            return None
        return await handler(event, data)
