from __future__ import annotations
"""Transactional Outbox Service.

This service implements the Message Relay pattern to process events
from the transactional outbox table and publish them to message brokers
(or invoke handlers directly).

It runs as a background process and:
1. Polls the outbox table for pending events
2. Processes each event via registered handlers
3. Marks events as processed on success, failed on error
4. Provides retry mechanism for failed events

Usage:
    outbox_service = TransactionalOutboxService(outbox_repository)
    await outbox_service.register_handler("order", order_handler)
    await outbox_service.start()
"""


import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Callable, Awaitable


from app.core.logger import get_logger

logger = get_logger(__name__)

EventHandler = Callable[[dict[str, Any]], Awaitable[bool]]


class TransactionalOutboxService:
    """Service for processing transactional outbox events.

    This implements the Message Relay pattern to ensure reliable
    event delivery.
    """

    def __init__(self, outbox_repository):
        self._outbox_repo = outbox_repository
        self._handlers: dict[str, EventHandler] = {}
        self._running = False
        self._poll_interval = 5.0
        self._max_retries = 3

    def register_handler(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for a specific event type.

        Args:
            event_type: The type of event to handle (e.g., "order.created")
            handler: Async function that processes the event
        """
        self._handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")

    def register_handlers(self, handlers: dict[str, EventHandler]) -> None:
        """Register multiple handlers at once."""
        for event_type, handler in handlers.items():
            self.register_handler(event_type, handler)

    async def process_pending_events(self, limit: int = 100) -> int:
        """Process all pending events in the outbox.

        Args:
            limit: Maximum number of events to process in one batch

        Returns:
            Number of events processed
        """
        if not self._outbox_repo:
            logger.warning("Outbox repository not configured")
            return 0

        events = await self._outbox_repo.get_pending_events(limit)
        processed_count = 0

        for event in events:
            event_id = event.get("id")
            event_type = event.get("event_type")
            aggregate_type = event.get("aggregate_type")
            aggregate_id = event.get("aggregate_id")

            try:
                payload = json.loads(event.get("payload", "{}"))
                full_event = {
                    "event_id": event_id,
                    "event_type": event_type,
                    "aggregate_type": aggregate_type,
                    "aggregate_id": aggregate_id,
                    "payload": payload,
                }

                handler_key = f"{aggregate_type}.{event_type}"
                handler = self._handlers.get(handler_key)

                if not handler:
                    logger.warning(f"No handler registered for {handler_key}, marking as processed")
                    await self._outbox_repo.mark_processed(event_id)
                    processed_count += 1
                    continue

                success = await handler(full_event)

                if success:
                    await self._outbox_repo.mark_processed(event_id)
                    processed_count += 1
                    logger.debug(f"Successfully processed event {event_id}: {handler_key}")
                else:
                    await self._outbox_repo.mark_failed(event_id, "Handler returned False")
                    logger.warning(f"Handler returned False for event {event_id}")

            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                logger.error(f"Error processing event {event_id}: {error_msg}")

                if event.get("retry_count", 0) < self._max_retries:
                    await self._outbox_repo.mark_failed(event_id, error_msg)
                else:
                    logger.error(f"Event {event_id} exceeded max retries, marking as dead")
                    await self._outbox_repo.mark_failed(event_id, f"Max retries exceeded: {error_msg}")

        return processed_count

    async def start(self, poll_interval: float = 5.0) -> None:
        """Start the outbox processor loop.

        Args:
            poll_interval: Seconds between polling for new events
        """
        self._running = True
        self._poll_interval = poll_interval
        logger.info(f"Starting outbox processor with poll interval: {poll_interval}s")

        while self._running:
            try:
                processed = await self.process_pending_events()
                if processed > 0:
                    logger.info(f"Processed {processed} outbox events")
            except Exception as e:
                logger.error(f"Error in outbox processor loop: {e}")

            await asyncio.sleep(self._poll_interval)

    def stop(self) -> None:
        """Stop the outbox processor."""
        self._running = False
        logger.info("Stopping outbox processor")


class OutboxPublisher:
    """Publisher that writes events to the outbox.

    This is the entry point for services that want to publish events
    reliably using the Transactional Outbox pattern.
    """

    def __init__(self, outbox_repository):
        self._outbox_repo = outbox_repository

    async def publish(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> int:
        """Publish an event to the outbox.

        This should be called within the same database transaction as
        the business operation to ensure atomicity.

        Args:
            aggregate_type: Type of aggregate (e.g., "order", "position")
            aggregate_id: ID of the aggregate
            event_type: Type of event (e.g., "created", "updated", "filled")
            payload: Event payload data

        Returns:
            ID of the created outbox record
        """
        return await self._outbox_repo.add_event(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
        )


def create_outbox_service(session_factory) -> TransactionalOutboxService:
    """Factory function to create outbox service with sync repository."""
    from app.infrastructure.repositories.outbox_repository import SyncOutboxRepository

    repo = SyncOutboxRepository(session_factory)
    return TransactionalOutboxService(repo)


async def create_async_outbox_service(database_uri: str) -> TransactionalOutboxService:
    """Factory function to create async outbox service."""
    from app.infrastructure.repositories.outbox_repository import OutboxRepository
    from app.infrastructure.database.async_mysql_client import create_async_session_factory

    session_factory = create_async_session_factory(database_uri)
    repo = OutboxRepository(session_factory)
    return TransactionalOutboxService(repo)


__all__ = [
    "TransactionalOutboxService",
    "OutboxPublisher",
    "create_outbox_service",
    "create_async_outbox_service",
]