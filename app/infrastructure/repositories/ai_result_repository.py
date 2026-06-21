from __future__ import annotations
"""AI Result Repository - caches AI analysis results for reuse.

This implements the result persistence and reuse strategy from midify_plan7.md:
- If same analysis request within 5 minutes, return cached result
- Reduces LLM API calls and improves response time
"""


import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any


from app.core.logger import get_logger

logger = get_logger(__name__)


class AIResultCache:
    """In-memory cache for AI analysis results with TTL."""

    def __init__(self, default_ttl_seconds: int = 300):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._ttl = default_ttl_seconds

    def _make_key(self, request_type: str, symbol: str, params: dict[str, Any]) -> str:
        """Generate cache key from request parameters."""
        key_data = f"{request_type}:{symbol}:{json.dumps(params, sort_keys=True)}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, request_type: str, symbol: str, params: dict[str, Any]) -> Any | None:
        """Get cached result if not expired."""
        key = self._make_key(request_type, symbol, params)
        if key in self._cache:
            result, timestamp = self._cache[key]
            age = time.time() - timestamp
            if age < self._ttl:
                logger.debug(f"AI cache hit: {request_type}:{symbol} (age: {age:.1f}s)")
                return result
            else:
                del self._cache[key]
                logger.debug(f"AI cache expired: {request_type}:{symbol}")
        return None

    def set(
        self,
        request_type: str,
        symbol: str,
        params: dict[str, Any],
        result: Any,
    ) -> None:
        """Cache result with timestamp."""
        key = self._make_key(request_type, symbol, params)
        self._cache[key] = (result, time.time())
        logger.debug(f"AI cache set: {request_type}:{symbol}")

    def invalidate(self, symbol: str | None = None) -> None:
        """Invalidate cache entries."""
        if symbol is None:
            self._cache.clear()
            return

        keys_to_delete = []
        for key in self._cache:
            if symbol in key:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self._cache[key]

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        now = time.time()
        active = 0
        expired = 0
        for _, (_, timestamp) in self._cache.items():
            if now - timestamp < self._ttl:
                active += 1
            else:
                expired += 1

        return {
            "total_entries": len(self._cache),
            "active": active,
            "expired": expired,
            "ttl_seconds": self._ttl,
        }


class AIResultRepository:
    """Repository for persisting AI analysis results.

    Provides both in-memory caching and optional persistent storage.
    """

    def __init__(self, session_factory: Any = None, ttl_seconds: int = 300):
        self._memory_cache = AIResultCache(ttl_seconds)
        self._session_factory = session_factory

    def save_result(
        self,
        request_type: str,
        symbol: str,
        params: dict[str, Any],
        result: Any,
    ) -> bool:
        """Save AI analysis result to cache."""
        self._memory_cache.set(request_type, symbol, params, result)

        if self._session_factory:
            self._persist_to_db(request_type, symbol, params, result)

        return True

    def get_cached_result(
        self,
        request_type: str,
        symbol: str,
        params: dict[str, Any],
    ) -> Any | None:
        """Get cached AI result if available and not expired."""
        cached = self._memory_cache.get(request_type, symbol, params)
        if cached is not None:
            return cached

        if self._session_factory:
            return self._load_from_db(request_type, symbol, params)

        return None

    def _persist_to_db(
        self,
        request_type: str,
        symbol: str,
        params: dict[str, Any],
        result: Any,
    ) -> None:
        """Persist to database for durability."""
        try:
            session = self._session_factory()
            from ..database.orm import AIAnalysisResult

            db_result = AIAnalysisResult(
                request_type=request_type,
                symbol=symbol,
                params_json=json.dumps(params),
                result_json=json.dumps(result) if isinstance(result, (dict, list)) else result,
                created_at=datetime.now(),
            )
            session.add(db_result)
            session.commit()
            session.close()
        except Exception as e:
            logger.warning(f"Failed to persist AI result to DB: {e}")

    def _load_from_db(
        self,
        request_type: str,
        symbol: str,
        params: dict[str, Any],
    ) -> Any | None:
        """Load recent result from database."""
        try:
            session = self._session_factory()
            from ..database.orm import AIAnalysisResult

            cutoff = datetime.now() - timedelta(seconds=self._memory_cache._ttl)
            record = (
                session.query(AIAnalysisResult)
                .filter(
                    AIAnalysisResult.request_type == request_type,
                    AIAnalysisResult.symbol == symbol,
                    AIAnalysisResult.created_at > cutoff,
                )
                .order_by(AIAnalysisResult.created_at.desc())
                .first()
            )

            session.close()

            if record:
                result = json.loads(record.result_json) if record.result_json else None
                if result:
                    self._memory_cache.set(request_type, symbol, params, result)
                    return result

        except Exception as e:
            logger.debug(f"Failed to load AI result from DB: {e}")

        return None

    def invalidate_symbol(self, symbol: str) -> None:
        """Invalidate all cached results for a symbol."""
        self._memory_cache.invalidate(symbol)

    def get_stats(self) -> dict[str, Any]:
        """Get repository statistics."""
        return self._memory_cache.stats()


def create_ai_result_repository(
    session_factory: Any = None,
    ttl_seconds: int = 300,
) -> AIResultRepository:
    """Factory function to create AI result repository."""
    return AIResultRepository(session_factory, ttl_seconds)