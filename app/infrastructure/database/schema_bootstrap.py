"""Schema bootstrap: Alembic upgrade (MySQL) with create_all fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_bool

logger = get_logger(__name__)


def alembic_enabled() -> bool:
    """MySQL uses Alembic by default; set ``DB_SCHEMA_CREATE_ALL=1`` to force create_all."""
    return not get_runtime_bool("DB_SCHEMA_CREATE_ALL", False)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def run_alembic_upgrade_head(*, ini_path: Path | None = None) -> None:
    """Run ``alembic upgrade head`` programmatically."""
    ini = ini_path or (_project_root() / "alembic.ini")
    if not ini.is_file():
        raise FileNotFoundError(f"Alembic config not found: {ini}")
    cfg = Config(str(ini))
    command.upgrade(cfg, "head")
    logger.info("Alembic upgrade head completed")


def bootstrap_schema(engine: Any) -> None:
    """Apply schema migrations.

    - SQLite: ``create_all`` only (Alembic env is MySQL-only).
    - MySQL + default: ``alembic upgrade head``, fallback to ``create_all`` on failure.
    - ``DB_SCHEMA_CREATE_ALL=1``: always ``create_all``.
    """
    from app.infrastructure.database import models  # noqa: F401
    from app.infrastructure.database.orm import Base

    dialect = (engine.dialect.name or "").lower()
    if dialect == "sqlite" or not alembic_enabled():
        Base.metadata.create_all(bind=engine)
        logger.info("Schema bootstrap via create_all (dialect=%s)", dialect or "unknown")
        return

    try:
        run_alembic_upgrade_head()
        from app.core.logging_config import reassert_logging_config

        reassert_logging_config()
    except Exception as exc:
        logger.warning(
            "Alembic upgrade failed, falling back to create_all: %s",
            exc,
            exc_info=True,
        )
        Base.metadata.create_all(bind=engine)
