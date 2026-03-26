"""
app/database_sync.py — Synchronous database session factory for Celery tasks.

Celery workers run in a synchronous context. Using asyncio.run() inside every task
creates a new event loop per invocation — functional but wasteful. This module
provides a psycopg2-backed synchronous SQLAlchemy session that Celery tasks can
use directly without the async overhead.

Usage in Celery tasks:
    from app.database_sync import get_sync_db

    with get_sync_db() as db:
        db.execute(text("SELECT 1"))
        db.commit()

The async engine (asyncpg) in database.py is still used by the FastAPI application.
Never use get_sync_db() in async code paths.
"""

from __future__ import annotations

import re
from collections.abc import Generator
from contextlib import contextmanager

import structlog
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

log = structlog.get_logger(__name__)

_sync_engine = None
_SyncSession: sessionmaker | None = None  # type: ignore[type-arg]


def _build_sync_url(async_url: str) -> str:
    """
    Convert asyncpg URL to psycopg2 URL.

    postgresql+asyncpg://user:pass@host:port/db
    →
    postgresql+psycopg2://user:pass@host:port/db
    """
    return re.sub(r"postgresql\+asyncpg://", "postgresql+psycopg2://", async_url, count=1)


def _get_sync_engine():  # type: ignore[return]
    """Return (or create) the synchronous SQLAlchemy engine. Lazy-initialised."""
    global _sync_engine, _SyncSession  # noqa: PLW0603

    if _sync_engine is not None:
        return _sync_engine

    settings = get_settings()
    sync_url = _build_sync_url(settings.database_url)

    _sync_engine = create_engine(
        sync_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=settings.debug,
    )

    @event.listens_for(_sync_engine, "connect")
    def set_search_path(dbapi_conn, connection_record):  # type: ignore[misc]
        cursor = dbapi_conn.cursor()
        cursor.execute("SET search_path TO public")
        cursor.close()

    _SyncSession = sessionmaker(
        bind=_sync_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    log.info("sync_db_engine_created", url=re.sub(r":([^@]+)@", ":***@", sync_url))
    return _sync_engine


@contextmanager
def get_sync_db() -> Generator[Session, None, None]:
    """
    Context manager that yields a synchronous SQLAlchemy session.

    The session is committed on clean exit and rolled back on exception.
    Always closed in the finally block.

    Example:
        with get_sync_db() as db:
            result = db.execute(text("SELECT id FROM companies LIMIT 10"))
            rows = result.fetchall()
    """
    _get_sync_engine()  # ensure engine + session factory are initialised

    if _SyncSession is None:
        raise RuntimeError("Sync session factory not initialised — call _get_sync_engine() first")

    session: Session = _SyncSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_sync_db_connection() -> bool:
    """
    Quick connectivity check for the sync DB.
    Returns True if the database is reachable, False otherwise.
    Used in Celery worker health checks.
    """
    try:
        with get_sync_db() as db:
            db.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        log.warning("sync_db_connection_failed", error=str(exc))
        return False
