"""Decision trace store with optional Redis persistence."""

from __future__ import annotations

import json
import logging
import threading
from typing import Any

from app.domain.dto.decision_context_dto import DecisionContextDTO

logger = logging.getLogger(__name__)

_TRACE_KEY_PREFIX = "quant:decision:trace:"
_DEFAULT_TTL_SECONDS = 7 * 24 * 3600


class DecisionTraceService:
    """Record and query ``DecisionContextDTO`` by ``decision_id``."""

    def __init__(
        self,
        *,
        max_entries: int = 5000,
        redis_url: str | None = None,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    ) -> None:
        self._max_entries = max(100, max_entries)
        self._ttl_seconds = max(3600, ttl_seconds)
        self._store: dict[str, DecisionContextDTO] = {}
        self._lock = threading.Lock()
        self._redis: Any = None
        if redis_url:
            self._connect_redis(redis_url)

    def _connect_redis(self, redis_url: str) -> None:
        try:
            from app.infrastructure.redis_client import RedisClientPool

            client = RedisClientPool.get(redis_url).client
            client.ping()
            self._redis = client
            logger.info("DecisionTraceService using Redis backend")
        except Exception as exc:
            logger.warning("DecisionTraceService Redis unavailable, using memory only: %s", exc)
            self._redis = None

    def _redis_key(self, decision_id: str) -> str:
        return f"{_TRACE_KEY_PREFIX}{decision_id}"

    def record(self, decision: DecisionContextDTO) -> DecisionContextDTO:
        """Persist a decision context for later trace lookup."""
        with self._lock:
            self._store[decision.decision_id] = decision
            if len(self._store) > self._max_entries:
                oldest = next(iter(self._store))
                del self._store[oldest]
        if self._redis is not None:
            try:
                self._redis.setex(
                    self._redis_key(decision.decision_id),
                    self._ttl_seconds,
                    decision.model_dump_json(),
                )
            except Exception as exc:
                logger.warning("DecisionTraceService Redis record failed: %s", exc)
        return decision

    def get(self, decision_id: str) -> DecisionContextDTO | None:
        """Fetch a decision trace by id."""
        with self._lock:
            cached = self._store.get(decision_id)
        if cached is not None:
            return cached
        if self._redis is None:
            return None
        try:
            raw = self._redis.get(self._redis_key(decision_id))
        except Exception as exc:
            logger.warning("DecisionTraceService Redis get failed: %s", exc)
            return None
        if not raw:
            return None
        try:
            decision = DecisionContextDTO.model_validate(json.loads(raw))
        except Exception as exc:
            logger.warning("DecisionTraceService trace decode failed: %s", exc)
            return None
        with self._lock:
            self._store[decision_id] = decision
        return decision

    def list_recent(self, *, limit: int = 50, subject_prefix: str | None = None) -> list[DecisionContextDTO]:
        """List recent traces, optionally filtered by subject prefix."""
        cap = min(max(limit, 1), 200)
        with self._lock:
            items = list(self._store.values())
        if subject_prefix:
            prefix = subject_prefix.strip()
            items = [d for d in items if d.subject.startswith(prefix)]
        return items[-cap:]

    def trace_payload(self, decision_id: str) -> dict[str, Any] | None:
        """Return a serializable trace bundle for API responses."""
        decision = self.get(decision_id)
        if decision is None:
            return None
        return {
            "decision_id": decision.decision_id,
            "subject": decision.subject,
            "created_at": decision.created_at,
            "model_version": decision.model_version,
            "input_snapshot": decision.input_snapshot,
            "reasoning_trace": decision.reasoning_trace,
            "evidence": [e.model_dump() for e in decision.evidence],
            "schema_version": decision.schema_version,
            "storage": "redis" if self._redis is not None else "memory",
        }


_trace_service: DecisionTraceService | None = None
_trace_lock = threading.Lock()


def get_decision_trace_service() -> DecisionTraceService:
    """Return the process-wide decision trace service singleton."""
    global _trace_service
    if _trace_service is None:
        with _trace_lock:
            if _trace_service is None:
                redis_url = None
                try:
                    from app.config import get_settings

                    settings = get_settings()
                    redis_url = (
                        getattr(settings, "task_message_redis_url", None)
                        or getattr(settings, "redis_url", None)
                    )
                except Exception as exc:
                    logger.debug("DecisionTraceService settings skipped: %s", exc)
                _trace_service = DecisionTraceService(redis_url=redis_url)
    return _trace_service


def reset_decision_trace_service() -> None:
    """Reset singleton (tests only)."""
    global _trace_service
    with _trace_lock:
        _trace_service = None


__all__ = ["DecisionTraceService", "get_decision_trace_service", "reset_decision_trace_service"]
