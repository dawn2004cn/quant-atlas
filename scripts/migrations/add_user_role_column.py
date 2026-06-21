"""Migration: add `role` VARCHAR column to users table if missing.

Fixes AttributeError when load_user calls _map_user which reads
u.role — the ORM model declares it, but the existing DB table
may not have the column.

Run once after deployment:
    python scripts/migrations/add_user_role_column.py
"""

from __future__ import annotations

import logging
import sys

from sqlalchemy import inspect, text

from app.config.settings import AppSettings
from app.infrastructure.database.orm import create_engine, create_session_factory, Base
from app.infrastructure.database.models import *  # noqa: F401  # Ensure all models are registered
from app.infrastructure.database.orm import mysql_database_uri

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def has_column(inspector, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    cols = inspector.get_columns(table_name)
    return any(c["name"] == column_name for c in cols)


def main():
    settings = AppSettings.from_env()

    if not settings.mysql:
        logger.error("MySQL is not configured. Cannot run migration.")
        sys.exit(1)

    db_url = mysql_database_uri(settings.mysql)
    logger.info("Connecting to database: %s", db_url.split("@")[-1] if "@" in db_url else db_url)

    engine = create_engine(db_url)
    session_factory = create_session_factory(engine)
    inspector = inspect(engine)

    session = session_factory()
    try:
        # Step 1: Add `role` column if missing
        if not has_column(inspector, "users", "role"):
            logger.info("Adding `role` VARCHAR(64) NOT NULL DEFAULT 'viewer' to users table...")
            session.execute(
                text("ALTER TABLE users ADD COLUMN role VARCHAR(64) NOT NULL DEFAULT 'viewer'")
            )
            session.commit()
            logger.info("Column `role` added successfully.")
        else:
            logger.info("Column `role` already exists on users table.")

        # Step 2: Populate `role` from role_id for any users missing it
        logger.info("Syncing `role` values from roles table...")
        rows = session.execute(text("SELECT id, code FROM roles")).fetchall()
        role_map = {int(r[0]): r[1] for r in rows}
        code_to_id = {r[1]: int(r[0]) for r in rows}

        # For users with role_id set, fill in the role code
        rows = session.execute(
            text(
                "SELECT id, role_id FROM users WHERE role_id IS NOT NULL AND (role IS NULL OR role = '')"
            )
        ).fetchall()
        synced = 0
        for uid, rid in rows:
            code = role_map.get(int(rid), "viewer")
            session.execute(
                text("UPDATE users SET role = :role WHERE id = :uid"),
                {"role": code, "uid": uid},
            )
            synced += 1
        session.commit()
        logger.info("Synced %d users with role values from role_id.", synced)

        # For users without role_id, derive role_id from existing role column value
        rows2 = session.execute(
            text(
                "SELECT id, role FROM users WHERE role IS NOT NULL AND role != '' AND role_id IS NULL"
            )
        ).fetchall()
        synced2 = 0
        for uid, role_val in rows2:
            role_val = str(role_val).strip().lower()
            rid = code_to_id.get(role_val)
            if rid is not None:
                session.execute(
                    text("UPDATE users SET role_id = :rid WHERE id = :uid"),
                    {"rid": rid, "uid": uid},
                )
                synced2 += 1
        if synced2:
            session.commit()
            logger.info("Synced %d users with role_id from role column.", synced2)

        logger.info("Migration complete.")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        session_factory.remove()
        engine.dispose()


if __name__ == "__main__":
    main()
