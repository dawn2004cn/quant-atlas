from __future__ import annotations

"""Port for MySQL DBAPI connections (pooled via infrastructure)."""

from typing import Any, Protocol


class MySQLConnectionPort(Protocol):
    """Application-facing MySQL connection access without importing mysql_client."""

    def connect(self, *, autocommit: bool = False) -> Any:
        """Return a DBAPI connection; caller must close to return to pool."""
        ...

    def ensure_schema(self, conn: Any = None) -> None:
        """Ensure required MySQL tables exist."""
        ...

    def commit(self, conn: Any) -> None:
        """Commit an open connection (infrastructure owns DBAPI semantics)."""
        ...

    def rollback(self, conn: Any) -> None:
        """Rollback an open connection."""
        ...
