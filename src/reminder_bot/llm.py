from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Literal, Optional

import httpx
from pydantic import BaseModel, ValidationError, field_validator

from .config import Settings
from .prompts import build_system_prompt
from .tz_utils import now_baku, weekday_ru

log = logging.getLogger(__name__)


class ParsedReminder(BaseModel):
    kind: Literal["once", "recurring", "error"]
    title: Optional[str] = None
    when_iso: Optional[str] = None
    cron: Optional[str] = None
    reason: Optional[str] = None

    @field_validator("title")
    @classmethod
    def _trim_title(cls, v):
        if v is None:
            return v
        return v.strip()[:200]


class LLMError(Exception):
    pass


async def _call_openrouter(settings: Settings, user_text: str, temperature: float = 0.1) -> dict:
    now = now_baku()
    system_prompt = build_system_prompt(now_baku_iso=now.isoformat(timespec="seconds"), weekday_ru=weekday_ru(now))
    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "temperature": temperature,
        "max_tokens": 250,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/sturvi4-cell/reminder",
        "X-Title": "Reminder Bot",
    }
    url = f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"

    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code in (429, 500, 502, 503, 504):
                last_exc = LLMError(f"OpenRouter {resp.status_code}: {resp.text[:200]}")
                await asyncio.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError, KeyError) as exc:
            last_exc = exc
            log.warning("OpenRouter attempt %d failed: %s", attempt + 1, exc)
            await asyncio.sleep(2 ** attempt)
    raise LLMError(f"OpenRouter request failed: {last_exc}")


async def parse_user_text(settings: Settings, user_text: str) -> ParsedReminder:
    raw = await _call_openrouter(settings, user_text, temperature=0.1)
    try:
        return ParsedReminder.model_validate(raw)
    except ValidationError as exc:
        log.warning("First parse failed (%s), retrying with temp=0", exc)
    raw = await _call_openrouter(settings, user_text, temperature=0.0)
    return ParsedReminder.model_validate(raw)
