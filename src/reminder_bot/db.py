from __future__ import annotations

import os
from pathlib import Path
from typing import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base

_engine = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def sqlite_url(db_path: str) -> str:
    return f"sqlite+aiosqlite:///{db_path}"


def sync_sqlite_url(db_path: str) -> str:
    return f"sqlite:///{db_path}"


async def init_db(db_path: str) -> None:
    global _engine, _sessionmaker
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    _engine = create_async_engine(sqlite_url(db_path), future=True)
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    if _sessionmaker is None:
        raise RuntimeError("DB not initialized. Call init_db() first.")
    async with _sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
