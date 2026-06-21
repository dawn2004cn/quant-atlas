from __future__ import annotations
"""Pure utility functions for trading domain value objects.

Extracted from psychology_execution_loader to break the
infrastructure → application dependency chain.
"""

import re

_USER_STRATEGY_RE = re.compile(r"^(?:retail_user_|user:|u:)(\d+)$", re.IGNORECASE)


def encode_retail_strategy_id(user_id: int) -> str:
    """Convention for binding QMT/execution rows to a retail user."""
    return f"retail_user_{int(user_id)}"


def parse_user_id_from_strategy_id(strategy_id: str | None) -> int | None:
    """Extract user_id from a strategy_id string."""
    if not strategy_id:
        return None
    text = str(strategy_id).strip()
    match = _USER_STRATEGY_RE.match(text)
    if match:
        return int(match.group(1))
    if text.isdigit():
        return int(text)
    return None
