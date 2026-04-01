"""
scripts/seed_db.py — Seed database with required initial data.

Creates:
  - Admin user — defaults: email `admin`, password `admin` (`ADMIN_EMAIL` / `ADMIN_PASSWORD`)
  - Demo partner user (development only) — defaults: `partner` / `partner` (`DEMO_PARTNER_*`)

Usage:
  python -m scripts.seed_db
  python -m scripts.seed_db --skip-if-seeded
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

log = logging.getLogger(__name__)


async def seed(skip_if_seeded: bool = False) -> None:
    from sqlalchemy.future import select
    from app.auth.models import User
    from app.auth.service import create_user, get_user_by_email
    from app.database import AsyncSessionLocal, check_db_connection

    if not await check_db_connection():
        log.error("Cannot connect to PostgreSQL — aborting seed")
        sys.exit(1)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        existing_users = result.scalars().all()

        if existing_users and skip_if_seeded:
            log.info("Database already seeded (%d users) — skipping", len(existing_users))
            return

        admin_email = os.getenv("ADMIN_EMAIL", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin")
        admin_name = os.getenv("ADMIN_NAME", "ORACLE Administrator")

        existing_admin = await get_user_by_email(db, admin_email)
        if existing_admin is None:
            admin = await create_user(db, admin_email, admin_password, admin_name, role="admin")
            log.info("Admin created: %s (id=%d)", admin.email, admin.id)
        else:
            log.info("Admin already exists: %s", admin_email)

        from app.config import get_settings
        settings = get_settings()

        if settings.is_development:
            demo_email = os.getenv("DEMO_PARTNER_EMAIL", "partner")
            demo_password = os.getenv("DEMO_PARTNER_PASSWORD", "partner")
            existing = await get_user_by_email(db, demo_email)
            if existing is None:
                partner = await create_user(db, demo_email, demo_password, "Demo Partner", role="partner")
                log.info("Demo partner created: %s (id=%d)", partner.email, partner.id)

        log.info("Seed complete")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-if-seeded", action="store_true")
    args = parser.parse_args()
    asyncio.run(seed(skip_if_seeded=args.skip_if_seeded))


if __name__ == "__main__":
    main()
