from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from interview.models import Base

logger = logging.getLogger("fair-hiring.interview.db")

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _to_asyncpg_url(url: str) -> str:
    """Convert postgres:// or postgresql:// URL to postgresql+asyncpg:// for SQLAlchemy."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def get_database_url() -> str:
    # Prefer non-pooling URL (direct connection) for asyncpg compatibility,
    # then fall back to pooling URL, then DATABASE_URL.
    raw = (
        os.environ.get("POSTGRES_URL_NON_POOLING")
        or os.environ.get("POSTGRES_URL")
        or os.environ.get("DATABASE_URL", "")
    )
    if not raw:
        raise RuntimeError(
            "No database URL configured. Set POSTGRES_URL_NON_POOLING, POSTGRES_URL, "
            "or DATABASE_URL environment variable."
        )
    return _to_asyncpg_url(raw)


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = get_database_url()
        _engine = create_async_engine(
            url,
            echo=os.environ.get("SQLALCHEMY_ECHO", "").lower() in ("1", "true", "yes"),
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def init_db() -> None:
    """Verify Postgres connectivity on startup. Tables are managed via migration scripts."""
    engine = get_engine()
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Interview database connection verified (PostgreSQL).")
    except Exception as exc:
        logger.error("Interview database connection failed: %s", exc)
        raise


async def dispose_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


async def get_session_dep() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        yield session
