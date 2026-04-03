"""Tests for psycopg2-safe PostgreSQL URL normalization."""

from app.db_url_sync import normalize_postgresql_url_for_psycopg2


def test_asyncpg_to_psycopg2() -> None:
    u = "postgresql+asyncpg://u:p@localhost:5432/db"
    assert normalize_postgresql_url_for_psycopg2(u) == "postgresql+psycopg2://u:p@localhost:5432/db"


def test_ssl_true_maps_to_sslmode_require() -> None:
    u = "postgresql+asyncpg://u:p@host:5432/db?ssl=true"
    out = normalize_postgresql_url_for_psycopg2(u)
    assert "postgresql+psycopg2://" in out
    assert "ssl=true" not in out
    assert "sslmode=require" in out


def test_ssl_false_maps_to_sslmode_disable() -> None:
    u = "postgresql://u:p@host:5432/db?ssl=false"
    out = normalize_postgresql_url_for_psycopg2(u)
    assert out.startswith("postgresql+psycopg2://")
    assert "sslmode=disable" in out


def test_preserves_existing_sslmode() -> None:
    u = "postgresql+asyncpg://u:p@h/db?ssl=true&sslmode=verify-full"
    out = normalize_postgresql_url_for_psycopg2(u)
    assert "sslmode=verify-full" in out
    assert "ssl=true" not in out
