from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    BOT_TOKEN: str = Field(min_length=10)

    OPENROUTER_API_KEY: str = Field(min_length=10)
    OPENROUTER_MODEL: str = "google/gemini-2.5-flash-lite"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    REGISTRATION_SECRET: str = Field(min_length=4)

    REPEAT_INTERVAL_MIN: int = Field(default=10, ge=1, le=1440)
    TIMEZONE: str = "Asia/Baku"
    DB_PATH: str = "/app/data/bot.db"
    LOG_LEVEL: str = "INFO"
