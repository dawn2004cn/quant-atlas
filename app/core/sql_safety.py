"""SQL identifier validation for dynamic table/column names in raw queries."""

from __future__ import annotations

import re

_TABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def safe_sql_identifier(name: str, default: str) -> str:
    """Return *name* when it matches a safe identifier pattern, else *default*."""
    raw = (name or default).strip()
    return raw if _TABLE_RE.match(raw) else default


# Backward-compatible alias used across timeseries modules.
safe_table_name = safe_sql_identifier

__all__ = ["safe_sql_identifier", "safe_table_name"]
