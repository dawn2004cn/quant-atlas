from __future__ import annotations

"""Release DB resources after Celery tasks (mirrors Flask teardown_appcontext)."""

from app.core.logger import get_logger

logger = get_logger(__name__)


def cleanup_worker_db_resources() -> None:
    """Return pooled MySQL connections and drop worker scoped SQLAlchemy sessions."""
    try:
        from app.infrastructure.database.mysql_client import mysql_close_thread_local_connection

        mysql_close_thread_local_connection()
    except Exception as exc:
        logger.debug("worker mysql cleanup skipped: %s", exc)

    try:
        from app.tasks.task_wiring import cleanup_worker_scoped_session

        cleanup_worker_scoped_session()
    except Exception as exc:
        logger.debug("worker scoped session cleanup skipped: %s", exc)
