"""
alembic/env.py — Alembic migration environment for ORACLE.

Migrations run synchronously via psycopg2 (sync URL). The FastAPI app uses asyncpg.
DATABASE_URL is read from the environment (not hardcoded in alembic.ini).
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection, engine_from_config

# Import Base and ALL models so Alembic can detect them for autogenerate
from app.database import Base
from app.auth.models import User  # noqa: F401
from app.models.signal import Signal  # noqa: F401 — table: signals
from app.models.company import Company, SignalRecord  # noqa: F401 — SignalRecord → signal_records
from app.models.client import Client, ChurnSignal, Prospect, BillingRecord, Matter  # noqa: F401
from app.models.trigger import Trigger, Alert  # noqa: F401
from app.models.ground_truth import GroundTruthLabel, LabelingRun  # noqa: F401
from app.models.bd_activity import (  # noqa: F401
    Alumni,
    BDActivity,
    ClientInquiry,
    ContentPiece,
    MatterSource,
    Partner,
    ReferralContact,
    WritingSample,
)
from app.models.scraper_health import ScraperHealth  # noqa: F401
from app.models.law_firm import LawFirm  # noqa: F401
from app.models.class_action_score import ClassActionScore  # noqa: F401
from app.models.geo import JetTrack, FootTrafficEvent, SatelliteSignal, PermitFiling  # noqa: F401
from app.models.training import TrainingDataset  # noqa: F401
from app.models.features import CompanyFeature  # noqa: F401

config = context.config

database_url = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://oracle:oracle@localhost:5432/oracle_db",
)
sync_database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
config.set_main_option("sqlalchemy.url", sync_database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url")
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    config.set_main_option("sqlalchemy.url", url)
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
