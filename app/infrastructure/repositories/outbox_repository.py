from __future__ import annotations

"""Transactional Outbox Repository.

This module implements the Transactional Outbox Pattern for reliable
event-driven communication between services.

Key benefits:
- Guarantees atomicity: Business operation + event publishing in same transaction
- Ensures eventual consistency: Events will be published even if broker is down
- Provides retry mechanism: Failed events can be retried
"""


import json
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.database.models.trading import TransactionalOutbox


class OutboxRepository:
    """Repository for managing transactional outbox messages."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None):
        self._session_factory = session_factory

    def _to_dict(self, model_obj: TransactionalOutbox) -> dict[str, Any]:
        return {c.name: getattr(model_obj, c.name) for c in model_obj.__table__.columns}

    async def add_event(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> int:
        """Add a new event to the outbox.

        This should be called within the same transaction as the business operation.
        """
        if self._session_factory:
            async with self._session_factory() as session:
                outbox = TransactionalOutbox(
                    aggregate_type=aggregate_type,
                    aggregate_id=aggregate_id,
                    event_type=event_type,
                    payload=json.dumps(payload, ensure_ascii=False),
                    status="pending",
                    created_at=datetime.now(),
                )
                session.add(outbox)
                await session.commit()
                return outbox.id

        raise RuntimeError("Session factory not configured")

    async def get_pending_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get pending events that haven't been processed."""
        if not self._session_factory:
            return []

        async with self._session_factory() as session:
            stmt = (
                select(TransactionalOutbox)
                .where(TransactionalOutbox.status == "pending")
                .order_by(TransactionalOutbox.created_at)
                .limit(limit)
            )
            result = await session.execute(stmt)
            events = result.scalars().all()
            return [self._to_dict(e) for e in events]

    async def mark_processed(self, event_id: int) -> bool:
        """Mark an event as processed."""
        if not self._session_factory:
            return False

        async with self._session_factory() as session:
            stmt = (
                update(TransactionalOutbox)
                .where(TransactionalOutbox.id == event_id)
                .values(status="processed", processed_at=datetime.now())
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def mark_failed(self, event_id: int, error_message: str) -> bool:
        """Mark an event as failed and increment retry count."""
        if not self._session_factory:
            return False

        async with self._session_factory() as session:
            stmt = (
                update(TransactionalOutbox)
                .where(TransactionalOutbox.id == event_id)
                .values(
                    status="failed",
                    last_error=error_message,
                    retry_count=TransactionalOutbox.retry_count + 1,
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def cleanup_processed(self, older_than_days: int = 7) -> int:
        """Clean up processed events older than specified days."""
        if not self._session_factory:
            return 0

        from datetime import timedelta

        async with self._session_factory() as session:
            cutoff = datetime.now() - timedelta(days=older_than_days)
            stmt = delete(TransactionalOutbox).where(
                TransactionalOutbox.status == "processed",
                TransactionalOutbox.processed_at < cutoff,
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount

    async def get_event(self, event_id: int) -> dict[str, Any] | None:
        """Get a specific event by ID."""
        if not self._session_factory:
            return None

        async with self._session_factory() as session:
            stmt = select(TransactionalOutbox).where(TransactionalOutbox.id == event_id)
            result = await session.execute(stmt)
            event = result.scalars().first()
            if not event:
                return None

            data = self._to_dict(event)
            data["payload"] = json.loads(event.payload)
            return data


class SyncOutboxRepository:
    """Synchronous version of OutboxRepository for legacy code."""

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    def add_event(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> int:
        """Add a new event to the outbox (sync version)."""
        if not self._session_factory:
            raise RuntimeError("Session factory not configured")

        session = self._session_factory()
        try:
            outbox = TransactionalOutbox(
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                event_type=event_type,
                payload=json.dumps(payload, ensure_ascii=False),
                status="pending",
                created_at=datetime.now(),
            )
            session.add(outbox)
            session.commit()
            return outbox.id
        finally:
            session.close()
            if hasattr(self._session_factory, "remove"):
                self._session_factory.remove()

    def get_pending_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get pending events (sync version)."""
        if not self._session_factory:
            return []

        session = self._session_factory()
        try:
            stmt = (
                select(TransactionalOutbox)
                .where(TransactionalOutbox.status == "pending")
                .order_by(TransactionalOutbox.created_at)
                .limit(limit)
            )
            result = session.execute(stmt)
            events = result.scalars().all()
            return [
                {c.name: getattr(e, c.name) for c in e.__table__.columns}
                for e in events
            ]
        finally:
            session.close()
            if hasattr(self._session_factory, "remove"):
                self._session_factory.remove()

    def mark_processed(self, event_id: int) -> bool:
        """Mark event as processed (sync version)."""
        if not self._session_factory:
            return False

        session = self._session_factory()
        try:
            stmt = (
                update(TransactionalOutbox)
                .where(TransactionalOutbox.id == event_id)
                .values(status="processed", processed_at=datetime.now())
            )
            result = session.execute(stmt)
            session.commit()
            return result.rowcount > 0
        finally:
            session.close()
            if hasattr(self._session_factory, "remove"):
                self._session_factory.remove()


__all__ = ["OutboxRepository", "SyncOutboxRepository"]
