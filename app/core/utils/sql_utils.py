"""SQL utility helpers — identifier validation, safe quoting, etc."""

import re

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_identifier(name: str) -> bool:
    """Validate that *name* is a safe SQL identifier (no injection risk).

    Accepts only ``[A-Za-z_][A-Za-z0-9_]*`` — the strictest subset of
    unquoted identifier characters common to MySQL, PostgreSQL, SQLite,
    ClickHouse, and QuestDB.

    Returns ``True`` if the name is safe, ``False`` otherwise.
    """
    if not isinstance(name, str) or not name.strip():
        return False
    return bool(_IDENTIFIER_RE.match(name.strip()))


def quote_identifier(name: str) -> str:
    """Return a backtick-quoted SQL identifier after validation."""
    cleaned = name.strip()
    if not validate_identifier(cleaned):
        raise ValueError(f"unsafe SQL identifier: {name!r}")
    return f"`{cleaned}`"