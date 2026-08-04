"""Deprecated shim — use ``app.infrastructure.events.cache_invalidation_subscriber``."""

from __future__ import annotations

import warnings


def __getattr__(name: str):
    if name == "CacheInvalidationSubscriber":
        warnings.warn(
            "app.domain.events.cache_invalidation_subscriber is deprecated; "
            "use app.infrastructure.events.cache_invalidation_subscriber",
            DeprecationWarning,
            stacklevel=2,
        )
        from app.infrastructure.events.cache_invalidation_subscriber import CacheInvalidationSubscriber

        return CacheInvalidationSubscriber
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
