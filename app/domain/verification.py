from __future__ import annotations

"""Analysis verification status driven by TruthSentry."""

import threading
from typing import Literal

VerificationStatus = Literal["verified", "pending", "stale"]

_lock = threading.Lock()
_pending: dict[str, str] = {}


def _key(symbol: str, market: str) -> str:
    return f"{(market or 'CN').strip().upper()}:{(symbol or '').strip().upper()}"


def mark_pending(symbol: str, market: str, *, reason: str) -> None:
    """Mark symbol analysis as pending verification."""
    key = _key(symbol, market)
    with _lock:
        _pending[key] = reason


def clear_pending(symbol: str, market: str) -> None:
    key = _key(symbol, market)
    with _lock:
        _pending.pop(key, None)


def get_verification_status(symbol: str, market: str) -> VerificationStatus:
    key = _key(symbol, market)
    with _lock:
        return "pending" if key in _pending else "verified"


def get_pending_reason(symbol: str, market: str) -> str | None:
    key = _key(symbol, market)
    with _lock:
        return _pending.get(key)


def list_pending() -> dict[str, str]:
    with _lock:
        return dict(_pending)
