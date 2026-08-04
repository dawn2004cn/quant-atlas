"""Deprecated shim — use ``app.infrastructure.events.cache_invalidation_publisher``."""

from __future__ import annotations

import warnings


def __getattr__(name: str):
    if name == "CacheInvalidationPublisher":
        warnings.warn(
            "app.domain.events.cache_invalidation_publisher is deprecated; "
            "use app.infrastructure.events.cache_invalidation_publisher",
            DeprecationWarning,
            stacklevel=2,
        )
        from app.infrastructure.events.cache_invalidation_publisher import CacheInvalidationPublisher

        return CacheInvalidationPublisher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
