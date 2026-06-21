from __future__ import annotations

"""Subscriber that consumes CacheInvalidationEvent from the outbox
and purges the corresponding cache entries.

This runs as a background worker (or Celery task) that polls the
TransactionalOutbox table for pending cache invalidation events,
applies them to the cache layer, and marks them processed.
"""

import json
import logging
from datetime import datetime, UTC, timedelta
from typing import Any

from app.domain.ports.cache_port import CachePort

logger = logging.getLogger(__name__)


class CacheInvalidationSubscriber:
    """Polls the outbox for cache invalidation events and purges affected cache entries."""

    BATCH_SIZE = 50
    MAX_RETRY_COUNT = 3

    def __init__(
        self,
        cache_port: CachePort,
        session_factory: Any,
        process_pending: bool = True,
    ) -> None:
        """
        Args:
            cache_port: Domain cache port for purging entries.
            session_factory: DB session factory for outbox reads.
            process_pending: If True, also process previously accumulated pending events on startup.
        """
        self._cache = cache_port
        self._session_factory = session_factory
        self._process_pending = process_pending

    def process_batch(self) -> int:
        """Process one batch of pending outbox events. Returns count processed."""
        from app.infrastructure.database.models.trading import TransactionalOutbox

        session = self._session_factory()
        try:
            # Fetch oldest pending events first
            pending = (
                session.query(TransactionalOutbox)
                .filter(
                    TransactionalOutbox.event_type == "CacheInvalidationEvent",
                    TransactionalOutbox.status == "pending",
                    TransactionalOutbox.retry_count < self.MAX_RETRY_COUNT,
                )
                .order_by(TransactionalOutbox.created_at.asc())
                .limit(self.BATCH_SIZE)
                .all()
            )

            if not pending:
                return 0

            processed = 0
            for record in pending:
                try:
                    payload = json.loads(record.payload)
                    namespace = payload.get("namespace", "")
                    invalidated_keys = payload.get("invalidated_keys", [])

                    # Apply invalidation
                    if invalidated_keys:
                        for key_pattern in invalidated_keys:
                            self._purge_key(key_pattern)
                    elif namespace:
                        self._purge_namespace(namespace)

                    # Mark as processed
                    record.status = "processed"
                    record.processed_at = datetime.now(UTC)
                    processed += 1

                except Exception:
                    logger.exception("Failed to process outbox record %s", record.id)
                    record.retry_count += 1
                    record.last_error = "Processing failed"

            session.commit()
            return processed

        except Exception:
            logger.exception("Batch processing failed")
            session.rollback()
            return 0
        finally:
            session.close()

    def _purge_key(self, key: str) -> None:
        """Delete a specific cache key."""
        try:
            self._cache.delete(key)
        except Exception:
            logger.warning("Cache delete failed for key: %s", key)

    def _purge_namespace(self, namespace: str) -> None:
        """Delete all keys under a namespace prefix."""
        try:
            self._cache.invalidate_prefix(namespace)
        except Exception:
            logger.warning("Cache namespace purge failed for: %s", namespace)
