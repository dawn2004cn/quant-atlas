from __future__ import annotations

"""PostgreSQL / TimescaleDB client helpers."""

from typing import Any

from app.core.logger import get_logger
from app.infrastructure.database.postgres_settings import PostgresSettings

logger = get_logger(__name__)


def postgres_connect(settings: PostgresSettings, *, autocommit: bool = False) -> Any:
    import psycopg

    conn = psycopg.connect(
        host=settings.host,
        port=settings.port,
        user=settings.user,
        password=settings.password,
        dbname=settings.database,
        autocommit=autocommit,
    )
    return conn


def ensure_timescaledb_extension(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
    if not conn.autocommit:
        conn.commit()
    logger.info("TimescaleDB extension ensured")


def ping_postgres(settings: PostgresSettings) -> bool:
    try:
        conn = postgres_connect(settings, autocommit=True)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("TimescaleDB ping failed: %s", exc)
        return False
