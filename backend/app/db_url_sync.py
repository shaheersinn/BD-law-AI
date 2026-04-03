"""
db_url_sync.py — Normalize PostgreSQL URLs for sync drivers (psycopg2).

libpq/psycopg2 reject the query parameter name ``ssl``; use ``sslmode`` instead.
Some managed DB URLs and async driver examples use ``ssl=true``, which breaks
Alembic and ``database_sync`` unless normalized.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def normalize_postgresql_url_for_psycopg2(url: str) -> str:
    """
    Prepare a PostgreSQL URL for SQLAlchemy + psycopg2 (sync / Alembic).

    - ``postgresql+asyncpg://`` -> ``postgresql+psycopg2://``
    - plain ``postgresql://`` -> ``postgresql+psycopg2://``
    - ``ssl=...`` -> ``sslmode=...`` when ``sslmode`` is not already set
    """
    if not url:
        return url

    u = url.strip()
    u = re.sub(r"^postgresql\+asyncpg://", "postgresql+psycopg2://", u, count=1)
    if u.startswith("postgresql://"):
        u = "postgresql+psycopg2://" + u[len("postgresql://") :]

    parsed = urlparse(u)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    has_sslmode = False
    out_pairs: list[tuple[str, str]] = []
    ssl_raw: str | None = None
    for key, val in pairs:
        lk = key.lower()
        if lk == "sslmode":
            has_sslmode = True
            out_pairs.append((key, val))
        elif lk == "ssl":
            ssl_raw = val
        else:
            out_pairs.append((key, val))

    if ssl_raw is not None and not has_sslmode:
        vl = str(ssl_raw).strip().lower()
        if vl in ("true", "1", "yes", "on"):
            out_pairs.append(("sslmode", "require"))
        elif vl in ("false", "0", "no", "off"):
            out_pairs.append(("sslmode", "disable"))
        else:
            out_pairs.append(("sslmode", str(ssl_raw)))

    new_query = urlencode(out_pairs)
    return urlunparse(parsed._replace(query=new_query))
