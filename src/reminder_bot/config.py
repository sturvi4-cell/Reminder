from __future__ import annotations

from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    BOT_TOKEN: str

    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "google/gemini-2.5-flash-lite"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    WHITELIST_USER_IDS: List[int] = Field(default_factory=list)
    WHITELIST_USERNAMES: List[str] = Field(default_factory=list)

    REPEAT_INTERVAL_MIN: int = 10
    TIMEZONE: str = "Asia/Baku"
    DB_PATH: str = "/app/data/bot.db"
    LOG_LEVEL: str = "INFO"

    @field_validator("WHITELIST_USER_IDS", mode="before")
    @classmethod
    def _ids(cls, v):
        if isinstance(v, str):
            return [int(x) for x in _parse_csv(v)]
        return v

    @field_validator("WHITELIST_USERNAMES", mode="before")
    @classmethod
    def _names(cls, v):
        if isinstance(v, str):
            return [x.lstrip("@").lower() for x in _parse_csv(v)]
        return v
