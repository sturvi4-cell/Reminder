from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def notification_kb(pending_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принято", callback_data=f"ack:{pending_id}")],
            [
                InlineKeyboardButton(text="⏰ 5 мин", callback_data=f"snz:{pending_id}:5"),
                InlineKeyboardButton(text="⏰ 15 мин", callback_data=f"snz:{pending_id}:15"),
                InlineKeyboardButton(text="⏰ 60 мин", callback_data=f"snz:{pending_id}:60"),
            ],
        ]
    )


def list_item_kb(reminder_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del:{reminder_id}")]
        ]
    )
