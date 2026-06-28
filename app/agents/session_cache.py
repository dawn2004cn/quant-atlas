from __future__ import annotations
"""Redis Session State Cache - Multi-Worker State Sharing.

This module implements from midify_plan13.md optimization:
- RedisSessionCache: Share ResearchState across Celery Workers
- Session-aware: Restore previous analysis context
- TTL support: Auto-expire stale sessions

Usage:
    cache = RedisSessionCache(redis_client)
    await cache.save_session("session_123", state)
    restored = await cache.get_session("session_123")
"""


import orjson as json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SessionState:
    """Session state for agent research."""
    session_id: str
    ticker: str
    state_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    ttl_seconds: int = 3600
    metadata: dict[str, Any] = field(default_factory=dict)


class RedisSessionCache:
    """Redis-backed session cache for distributed agent execution.

    Features:
    - Multi-worker state sharing
    - Automatic TTL expiration
    - Session restoration for follow-up queries
    """

    def __init__(
        self,
        redis_client: Any = None,
        prefix: str = "agent:session:",
        default_ttl: int = 3600,
    ):
        self._redis = redis_client
        self._prefix = prefix
        self._default_ttl = default_ttl
        self._local_cache: dict[str, SessionState] = {}

    def _make_key(self, session_id: str) -> str:
        """Create Redis key for session."""
        return f"{self._prefix}{session_id}"

    async def save_session(
        self,
        session_id: str,
        state: dict[str, Any],
        ttl_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Save session state to Redis."""
        session = SessionState(
            session_id=session_id,
            ticker=state.get("ticker", ""),
            state_data=state,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            ttl_seconds=ttl_seconds or self._default_ttl,
            metadata=metadata or {},
        )

        self._local_cache[session_id] = session

        if self._redis:
            try:
                key = self._make_key(session_id)
                serialized = json.dumps({
                    "session_id": session_id,
                    "ticker": session.ticker,
                    "state_data": session.state_data,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "metadata": session.metadata,
                }, default=str)

                await self._redis.setex(key, session.ttl_seconds, serialized)
                logger.info(f"Saved session {session_id} to Redis")
                return True
            except Exception as e:
                logger.error(f"Failed to save session to Redis: {e}")

        return False

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session state from Redis."""
        if session_id in self._local_cache:
            return self._local_cache[session_id].state_data

        if self._redis:
            try:
                key = self._make_key(session_id)
                data = await self._redis.get(key)

                if data:
                    parsed = json.loads(data)
                    session = SessionState(
                        session_id=parsed["session_id"],
                        ticker=parsed.get("ticker", ""),
                        state_data=parsed.get("state_data", {}),
                        created_at=datetime.fromisoformat(parsed["created_at"]),
                        updated_at=datetime.fromisoformat(parsed["updated_at"]),
                        metadata=parsed.get("metadata", {}),
                    )
                    self._local_cache[session_id] = session
                    return session.state_data
            except Exception as e:
                logger.error(f"Failed to get session from Redis: {e}")

        return None

    async def update_session(
        self,
        session_id: str,
        updates: dict[str, Any],
    ) -> bool:
        """Update specific fields in session."""
        current = await self.get_session(session_id)
        if not current:
            return False

        current.update(updates)
        return await self.save_session(session_id, current)

    async def delete_session(self, session_id: str) -> bool:
        """Delete session from cache."""
        if session_id in self._local_cache:
            del self._local_cache[session_id]

        if self._redis:
            try:
                key = self._make_key(session_id)
                await self._redis.delete(key)
                return True
            except Exception as e:
                logger.error(f"Failed to delete session: {e}")

        return False

    async def list_active_sessions(self) -> list[str]:
        """List all active session IDs."""
        if self._redis:
            try:
                pattern = f"{self._prefix}*"
                keys = []
                async for key in self._redis.scan_iter(match=pattern):
                    keys.append(key.decode() if isinstance(key, bytes) else key)

                return [k.replace(self._prefix, "") for k in keys]
            except Exception as e:
                logger.error(f"Failed to list sessions: {e}")

        return list(self._local_cache.keys())

    async def extend_ttl(self, session_id: str, additional_seconds: int = 3600) -> bool:
        """Extend session TTL."""
        if self._redis:
            try:
                key = self._make_key(session_id)
                await self._redis.expire(key, additional_seconds)
                return True
            except Exception as e:
                logger.error(f"Failed to extend TTL: {e}")

        return False


class SessionManager:
    """High-level session management for agent workflows."""

    def __init__(self, cache: RedisSessionCache | None = None):
        self._cache = cache or RedisSessionCache()

    async def start_session(
        self,
        session_id: str,
        ticker: str,
        initial_state: dict[str, Any],
    ) -> bool:
        """Start a new research session."""
        return await self._cache.save_session(
            session_id,
            initial_state,
            metadata={"ticker": ticker, "status": "active"},
        )

    async def continue_session(
        self,
        session_id: str,
        additional_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Continue existing session with new state."""
        current = await self._cache.get_session(session_id)
        if current:
            current.update(additional_state)
            await self._cache.save_session(session_id, current)

        return current or additional_state

    async def end_session(
        self,
        session_id: str,
        final_state: dict[str, Any] | None = None,
    ) -> bool:
        """End session and optionally save final state."""
        if final_state:
            await self._cache.save_session(
                session_id,
                final_state,
                metadata={"status": "completed"},
            )

        return True


_global_session_cache: RedisSessionCache | None = None


def get_session_cache() -> RedisSessionCache:
    """Get singleton session cache."""
    global _global_session_cache
    if _global_session_cache is None:
        _global_session_cache = RedisSessionCache()
    return _global_session_cache
