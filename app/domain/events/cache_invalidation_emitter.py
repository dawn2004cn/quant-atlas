from __future__ import annotations

"""Convenience helpers for emitting cache invalidation events from business operations.

Call these inside your DB transaction to atomically persist the event
to the outbox. A background Celery task or polling worker will consume
them and purge the affected cache entries.
"""

import logging
from typing import Any

from app.domain.events.cache_invalidation import (
    CacheInvalidationEvent,
    invalidate_market_panorama,
    invalidate_quote,
    invalidate_strategy_cache,
)

logger = logging.getLogger(__name__)


class CacheInvalidationEmitter:
    """Emits CacheInvalidationEvent to the outbox within a DB transaction.

    Usage:
        emitter = CacheInvalidationEmitter(session_factory)
        with emitter.in_transaction() as tx:
            # ... do business work ...
            tx.emit(invalidate_quote("600519", "CN"))
            # ... more work ...
        # on commit, all outbox records are flushed
    """

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    def in_transaction(self) -> CacheInvalidationTransaction:
        return CacheInvalidationTransaction(self._session_factory)


class CacheInvalidationTransaction:
    """Context manager that batches outbox writes and flushes on commit."""

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory
        self._events: list[CacheInvalidationEvent] = []

    def emit(self, event: CacheInvalidationEvent) -> None:
        """Queue an event for emission on commit."""
        self._events.append(event)

    def __enter__(self) -> CacheInvalidationTransaction:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            return  # Don't flush on exception

        from app.infrastructure.database.models.trading import TransactionalOutbox
        import json

        session = self._session_factory()
        try:
            for event in self._events:
                record = TransactionalOutbox(
                    aggregate_type=event.aggregate_type,
                    aggregate_id=event.aggregate_id,
                    event_type=event.event_type,
                    payload=json.dumps(event.to_payload()),
                    status="pending",
                )
                session.add(record)
            session.flush()
            # Caller controls commit — we only flush within the transaction
        except Exception:
            logger.exception("Failed to flush cache invalidation events")
            session.rollback()
        finally:
            session.close()
