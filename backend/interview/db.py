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


def normalize_database_url(raw: str) -> str:
    """
    SQLAlchemy async Postgres requires the asyncpg driver in the URL scheme.

    Supabase (and some hosts) ship ``postgres://`` or ``postgresql://`` without ``+asyncpg``.
    The Supabase *transaction* pooler (port 6543 / ``*.pooler.supabase.com``) is PgBouncer in
    transaction mode — asyncpg must disable its prepared-statement cache for that endpoint.
    """
    u = raw.strip().strip('"').strip("'")
    if not u:
        return u
    if u.startswith("postgresql+asyncpg://"):
        return u
    if u.startswith("postgres://"):
        return "postgresql+asyncpg://" + u[len("postgres://") :]
    if u.startswith("postgresql://"):
        return "postgresql+asyncpg://" + u[len("postgresql://") :]
    return u


def get_database_url() -> str:
    """Resolve Postgres URL from common platform env names (Vercel, Neon, Supabase, FastAPI Cloud)."""
    keys = (
        "POSTGRES_URL_NON_POOLING",
        "POSTGRES_URL",
        "DATABASE_URL",
        "DATABASE_PRIVATE_URL",  # some hosts expose direct connection under this name
        "NEON_DATABASE_URL",
        "SUPABASE_DB_URL",
    )
    raw = ""
    for key in keys:
        v = os.environ.get(key, "").strip()
        if v:
            raw = v
            break
    if not raw:
        raise RuntimeError(
            "No database URL configured. Set one of: "
            + ", ".join(keys)
            + ". "
            "On FastAPI Cloud: Dashboard → your app → Environment variables → add DATABASE_URL "
            "(your Supabase/Neon Postgres URI). `.env` is not shipped with the image unless you "
            "inject it as secrets there."
        )
    return normalize_database_url(raw)


def _asyncpg_connect_args(url: str) -> dict:
    """PgBouncer transaction pooler (Supabase :6543) is incompatible with asyncpg's statement cache."""
    lower = url.lower()
    if "pooler.supabase.com" in lower or ":6543/" in lower or ":6543?" in lower:
        return {"statement_cache_size": 0}
    return {}


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = get_database_url()
        kwargs: dict = {
            "echo": os.environ.get("SQLALCHEMY_ECHO", "").lower() in ("1", "true", "yes"),
            "pool_size": 5,
            "max_overflow": 10,
        }
        if url.startswith("postgresql+asyncpg"):
            ca = _asyncpg_connect_args(url)
            if ca:
                kwargs["connect_args"] = ca
        _engine = create_async_engine(url, **kwargs)
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
    """Verify Postgres connectivity; optionally create interview tables from models (no Alembic in-repo)."""
    engine = get_engine()
    auto_create = os.environ.get("INTERVIEW_AUTO_CREATE_TABLES", "1").lower() not in (
        "0",
        "false",
        "no",
    )
    try:
        async with engine.begin() as conn:
            if auto_create:
                await conn.run_sync(Base.metadata.create_all)
            from sqlalchemy import text

            await conn.execute(text("SELECT 1"))
        if auto_create:
            logger.info("Interview database ready (PostgreSQL, tables ensured via create_all).")
        else:
            logger.info("Interview database connection verified (PostgreSQL).")
    except Exception as exc:
        logger.error("Interview database init failed: %s", exc)
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
