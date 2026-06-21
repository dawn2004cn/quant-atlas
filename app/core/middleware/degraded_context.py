"""Request-scoped degraded-mode flag for resilience mesh."""

from __future__ import annotations

import contextvars

_degraded: contextvars.ContextVar[bool] = contextvars.ContextVar("system_degraded", default=False)
_degraded_reasons: contextvars.ContextVar[tuple[str, ...]] = contextvars.ContextVar(
    "degraded_reasons",
    default=(),
)


def mark_system_degraded(reason: str) -> None:
    """Mark the current request as operating in degraded mode."""
    label = (reason or "unknown").strip()
    if not label:
        return
    _degraded.set(True)
    current = _degraded_reasons.get()
    if label not in current:
        _degraded_reasons.set(current + (label,))


def is_system_degraded() -> bool:
    return _degraded.get()


def get_degraded_reasons() -> list[str]:
    return list(_degraded_reasons.get())


def clear_degraded_state() -> None:
    _degraded.set(False)
    _degraded_reasons.set(())


__all__ = [
    "mark_system_degraded",
    "is_system_degraded",
    "get_degraded_reasons",
    "clear_degraded_state",
]
