"""Upper bounds for unbounded ORM / list queries."""

from __future__ import annotations

MAX_WATCHLIST_SYMBOLS = 500
MAX_STOCK_GROUP_SYMBOLS = 500
MAX_USER_TEAMS = 50
MAX_USERS = 1000

__all__ = [
    "MAX_STOCK_GROUP_SYMBOLS",
    "MAX_USER_TEAMS",
    "MAX_USERS",
    "MAX_WATCHLIST_SYMBOLS",
]
