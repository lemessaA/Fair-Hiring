from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy import text
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


def _default_database_url() -> str:
    backend_dir = Path(__file__).resolve().parent.parent
    db_path = backend_dir / "interview.db"
    return f"sqlite+aiosqlite:///{db_path}"


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", _default_database_url())


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = get_database_url()
        _engine = create_async_engine(
            url,
            echo=os.environ.get("SQLALCHEMY_ECHO", "").lower() in ("1", "true", "yes"),
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


async def _ensure_sqlite_session_columns(conn) -> None:
    """SQLite create_all does not add new columns; patch interview_session if needed."""
    url = get_database_url()
    if "sqlite" not in url.lower():
        return
    res = await conn.execute(text("PRAGMA table_info(interview_session)"))
    rows = res.fetchall()
    names = {r[1] for r in rows}
    if "hire_decision" not in names:
        await conn.execute(
            text("ALTER TABLE interview_session ADD COLUMN hire_decision VARCHAR(16)")
        )
        logger.info("SQLite: added interview_session.hire_decision")
    if "hire_rationale" not in names:
        await conn.execute(text("ALTER TABLE interview_session ADD COLUMN hire_rationale TEXT"))
        logger.info("SQLite: added interview_session.hire_rationale")


async def init_db() -> None:
    if os.environ.get("INTERVIEW_AUTO_CREATE_TABLES", "1").lower() not in (
        "1",
        "true",
        "yes",
    ):
        return
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_sqlite_session_columns(conn)
    logger.info("Interview ORM tables ensured (create_all).")


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
