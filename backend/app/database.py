"""
app/database.py — Database connections for ORACLE.

Two databases:
  1. PostgreSQL (asyncpg) — structured data: companies, signals, features, scores, labels
  2. MongoDB Atlas (motor) — unstructured: social signals, corporate graph, scraped docs

Design decisions:
  - Async SQLAlchemy 2.0 with asyncpg driver (fastest async PostgreSQL driver)
  - motor async client for MongoDB (official async MongoDB driver)
  - Connection pool settings tuned for production workloads
  - Separate session factories for different use cases
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

log = logging.getLogger(__name__)

settings = get_settings()


# ── SQLAlchemy Base ────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """
    Declarative base for all SQLAlchemy ORM models.

    All models in app/models/ must inherit from this class.
    Metadata is shared across all models for Alembic migration discovery.
    """
    pass


# ── PostgreSQL Engine ──────────────────────────────────────────────────────────

def _create_engine() -> AsyncEngine:
    """
    Create the async SQLAlchemy engine with production-tuned settings.

    Pool settings:
      - pool_size=20: handles 20 concurrent DB connections
      - max_overflow=10: allows 10 additional connections under load
      - pool_timeout=30: raises error after 30s waiting for connection
      - pool_recycle=3600: recycle connections after 1 hour (avoids stale connections)
      - pool_pre_ping=True: test connections before use (catches dropped connections)
    """
    return create_async_engine(
        settings.database_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,  # Critical: test connection health before each use
        # JSON serialization for PostgreSQL JSONB columns
        json_serializer=None,
        json_deserializer=None,
    )


engine: AsyncEngine = _create_engine()

# Session factory — use this everywhere via get_db() dependency
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit (better for async)
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.

    Usage in routes:
        @router.get("/companies")
        async def list_companies(db: AsyncSession = Depends(get_db)):
            ...

    The session is automatically closed after the request completes.
    Exceptions trigger rollback, not commit.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """
    Check PostgreSQL connectivity. Used in health check and startup.

    Returns:
        True if connected, False if unreachable.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        log.error("PostgreSQL health check failed", error=str(e))
        return False


async def dispose_engine() -> None:
    """
    Dispose the engine connection pool on application shutdown.
    Called from FastAPI lifespan context manager.
    """
    await engine.dispose()
    log.info("PostgreSQL engine disposed")


# ── MongoDB Client ─────────────────────────────────────────────────────────────

_mongo_client: AsyncIOMotorClient | None = None
_mongo_db: AsyncIOMotorDatabase | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    """
    Return singleton MongoDB client.

    Motor (async MongoDB driver) manages its own connection pool.
    A single client instance is reused across the application.
    """
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(
            settings.mongodb_url,
            maxPoolSize=settings.mongodb_max_pool_size,
            serverSelectionTimeoutMS=5000,  # 5s timeout for server selection
            connectTimeoutMS=10000,          # 10s connection timeout
            socketTimeoutMS=30000,           # 30s socket timeout
        )
        log.info("MongoDB client created", url=settings.mongodb_url[:30] + "...")
    return _mongo_client


def get_mongo_db() -> AsyncIOMotorDatabase:
    """
    Return the MongoDB database instance.

    Collections used:
      - social_signals: Reddit, Twitter, LinkedIn, Stockhouse posts
      - corporate_graph: Company nodes, director edges, auditor edges
      - law_firm_posts: Law firm blog posts and case commentaries
      - scraped_documents: Raw scraped content with lineage metadata
      - signal_cache: Cached signal computations with TTL

    Usage in routes/services:
        db = get_mongo_db()
        collection = db["social_signals"]
        await collection.insert_one(doc)
    """
    global _mongo_db
    if _mongo_db is None:
        client = get_mongo_client()
        _mongo_db = client[settings.mongodb_db_name]
    return _mongo_db


async def get_mongo_db_dep() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """
    FastAPI dependency that provides MongoDB database.

    Usage in routes:
        @router.post("/signals")
        async def create_signal(
            mongo: AsyncIOMotorDatabase = Depends(get_mongo_db_dep)
        ):
            ...
    """
    yield get_mongo_db()


async def check_mongo_connection() -> bool:
    """
    Check MongoDB connectivity. Used in health check and startup.

    Returns:
        True if connected, False if unreachable.
    """
    try:
        client = get_mongo_client()
        await client.admin.command("ping")
        return True
    except Exception as e:
        log.error("MongoDB health check failed", error=str(e))
        return False


async def close_mongo_connection() -> None:
    """
    Close MongoDB client on application shutdown.
    Called from FastAPI lifespan context manager.
    """
    global _mongo_client, _mongo_db
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
        _mongo_db = None
        log.info("MongoDB client closed")
