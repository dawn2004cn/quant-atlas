"""Publisher that persists CacheInvalidationEvent to the Transactional Outbox."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.domain.events.cache_invalidation import CacheInvalidationEvent
from app.infrastructure.database.models.trading import TransactionalOutbox

logger = logging.getLogger(__name__)


class CacheInvalidationPublisher:
    """Writes cache invalidation events to the outbox within a DB transaction."""

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    def publish(self, event: CacheInvalidationEvent) -> None:
        """Persist the event to the outbox table inside the caller's transaction."""
        session = self._session_factory()
        try:
            outbox_record = TransactionalOutbox(
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                event_type=event.event_type,
                payload=json.dumps(event.to_payload()),
                status="pending",
            )
            session.add(outbox_record)
            session.flush()
        except Exception:
            logger.exception("Failed to persist cache invalidation event: %s", event.namespace)
            session.rollback()
            raise
