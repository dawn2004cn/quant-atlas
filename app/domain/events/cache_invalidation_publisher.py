from __future__ import annotations

"""Publisher that persists CacheInvalidationEvent to the Transactional Outbox.

Usage:
    publisher = CacheInvalidationPublisher(session_factory)
    publisher.publish(invalidate_quote("600519", "CN"))

The event is written inside the caller's DB transaction — atomic with
the business operation that caused the cache to become stale.
"""

import logging
from typing import Any

from app.domain.events.cache_invalidation import CacheInvalidationEvent

logger = logging.getLogger(__name__)


class CacheInvalidationPublisher:
    """Writes cache invalidation events to the outbox within a DB transaction."""

    def __init__(self, session_factory: Any) -> None:
        """
        Args:
            session_factory: Callable returning a DB session (scoped/sessionmaker).
        """
        self._session_factory = session_factory

    def publish(self, event: CacheInvalidationEvent) -> None:
        """Persist the event to the outbox table.

        MUST be called inside an active DB transaction so that the
        business data change and the outbox record are committed atomically.
        """
        from app.infrastructure.database.models.trading import TransactionalOutbox

        session = self._session_factory()
        try:
            outbox_record = TransactionalOutbox(
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                event_type=event.event_type,
                payload=self._json.dumps(event.to_payload()),
                status="pending",
            )
            session.add(outbox_record)
            # Do NOT commit — the caller controls the transaction boundary.
            # Flush to ensure the record is visible within the same transaction.
            session.flush()
        except Exception:
            logger.exception("Failed to persist cache invalidation event: %s", event.namespace)
            session.rollback()
            raise

    @property
    def _json(self) -> Any:
        import json
        return json
