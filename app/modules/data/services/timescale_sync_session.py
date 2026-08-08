from __future__ import annotations

"""Per-thread TimescaleDB sync session (connection reuse across stocks on same worker)."""

import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.infrastructure.repositories.postgres.postgres_timescale_bar_repository import (
        TimescaleSyncSession,
    )

_tls = threading.local()


def get_thread_timescale_session() -> TimescaleSyncSession | None:
    return getattr(_tls, "session", None)


def set_thread_timescale_session(session: TimescaleSyncSession | None) -> None:
    _tls.session = session


def close_thread_timescale_session() -> None:
    sess = getattr(_tls, "session", None)
    if sess is not None:
        sess.close()
        _tls.session = None
