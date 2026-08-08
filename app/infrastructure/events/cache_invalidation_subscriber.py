"""Subscriber that consumes cache invalidation events from the outbox."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.domain.ports.cache_port import CachePort
from app.infrastructure.database.models.trading import TransactionalOutbox

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
        self._cache = cache_port
        self._session_factory = session_factory
        self._process_pending = process_pending

    def process_batch(self) -> int:
        """Process one batch of pending outbox events. Returns count processed."""
        session = self._session_factory()
        try:
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

                    if invalidated_keys:
                        for key_pattern in invalidated_keys:
                            self._purge_key(key_pattern)
                    elif namespace:
                        self._purge_namespace(namespace)

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
        try:
            self._cache.delete(key)
        except Exception:
            logger.warning("Cache delete failed for key: %s", key)

    def _purge_namespace(self, namespace: str) -> None:
        try:
            self._cache.invalidate_prefix(namespace)
        except Exception:
            logger.warning("Cache namespace purge failed for: %s", namespace)
