"""Signal-flag pool repository facade (MySQL/SQLite via RepositoryRegistry)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..factory import RepositoryType, create_repository

# Populate RepositoryRegistry on import.
from ..register import ensure_registered

ensure_registered()


def _build(
    *,
    mysql: Any = None,
    session_factory: Any = None,
    db_path: Path | str | None = None,
) -> Any:
    if mysql is not None:
        return create_repository(
            RepositoryType.MYSQL,
            "signal_flag_pool",
            mysql=mysql,
            session_factory=session_factory,
        )
    path = Path(db_path) if db_path is not None else Path("instance/signal_flag_pool.db")
    return create_repository(
        RepositoryType.SQLITE,
        "signal_flag_pool",
        db_path=path,
    )


class SignalFlagPoolRepository:
    """Legacy facade matching ``SignalFlagPoolRepository(mysql=..., session_factory=...)``."""

    def __init__(
        self,
        *,
        mysql: Any = None,
        session_factory: Any = None,
        db_path: Path | str | None = None,
    ) -> None:
        self._delegate = _build(
            mysql=mysql,
            session_factory=session_factory,
            db_path=db_path,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)


__all__ = ["SignalFlagPoolRepository"]
