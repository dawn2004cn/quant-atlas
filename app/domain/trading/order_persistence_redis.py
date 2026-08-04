"""Deprecated shim — use ``app.infrastructure.trading.order_persistence_redis``."""

from __future__ import annotations

import warnings


def __getattr__(name: str):
    if name == "RedisOrderPersistenceBackend":
        warnings.warn(
            "app.domain.trading.order_persistence_redis is deprecated; "
            "use app.infrastructure.trading.order_persistence_redis",
            DeprecationWarning,
            stacklevel=2,
        )
        from app.infrastructure.trading.order_persistence_redis import RedisOrderPersistenceBackend

        return RedisOrderPersistenceBackend
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
