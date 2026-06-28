from __future__ import annotations

"""Distributed Blackboard Persistence - Redis Backend Implementation.

This module implements from midify_plan12.md:
- RedisEvidenceBlackboard: Distributed blackboard using Redis
- Cluster-aware: Supports multiple Celery Workers
- Atomic operations: Ensures consistency across distributed environment

Usage:
    blackboard = RedisEvidenceBlackboard(redis_client=redis)
    blackboard.write_evidence("ticker", "pe_ratio", 25.0, "fundamental")
    # Read from any worker in the cluster
"""


from dataclasses import dataclass
from datetime import datetime
from typing import Any

import orjson as json

from app.core.logger import get_logger

from .evidence_blackboard import (
    EvidenceBlackboard,
    EvidenceStrength,
    EvidenceType,
)

logger = get_logger(__name__)


@dataclass
class DistributedEvidence:
    """Evidence stored in distributed blackboard."""
    key: str
    value: Any
    evidence_type: str
    strength: str
    source_agent: str
    timestamp: datetime
    ttl_seconds: int = 3600


class RedisEvidenceBlackboard(EvidenceBlackboard):
    """Distributed evidence blackboard using Redis backend.

    Preserves EvidenceBlackboard interface while providing:
    - Redis persistence for distributed workers
    - Atomic operations for consistency
    - TTL-based expiration
    """

    def __init__(
        self,
        redis_client: Any = None,
        namespace: str = "blackboard",
        default_ttl: int = 3600,
    ):
        self._redis = redis_client
        self._namespace = namespace
        self._default_ttl = default_ttl
        self._local_cache: dict[str, DistributedEvidence] = {}

    def _make_key(self, ticker: str, key: str) -> str:
        """Create Redis key."""
        return f"{self._namespace}:{ticker}:{key}"

    def _parse_key(self, redis_key: str) -> tuple[str, str]:
        """Parse Redis key to ticker and evidence key."""
        parts = redis_key.split(":")
        if len(parts) >= 3:
            return parts[1], parts[2]
        return "", ""

    async def write_evidence(
        self,
        ticker: str,
        key: str,
        value: Any,
        evidence_type: EvidenceType = EvidenceType.OTHER,
        strength: EvidenceStrength = EvidenceStrength.MEDIUM,
        source_agent: str = "system",
        ttl_seconds: int | None = None,
    ) -> None:
        """Write evidence to distributed blackboard."""
        evidence = DistributedEvidence(
            key=key,
            value=value,
            evidence_type=evidence_type.value,
            strength=strength.value,
            source_agent=source_agent,
            timestamp=datetime.now(),
            ttl_seconds=ttl_seconds or self._default_ttl,
        )

        self._local_cache[f"{ticker}:{key}"] = evidence

        if self._redis:
            try:
                redis_key = self._make_key(ticker, key)
                serialized = json.dumps({
                    "key": key,
                    "value": value,
                    "evidence_type": evidence.evidence_type,
                    "strength": evidence.strength,
                    "source_agent": source_agent,
                    "timestamp": evidence.timestamp.isoformat(),
                }, default=str)

                await self._redis.setex(redis_key, evidence.ttl_seconds, serialized)
                logger.debug(f"Written to Redis: {redis_key}")
            except Exception as e:
                logger.error(f"Failed to write to Redis: {e}")

    async def read_evidence(
        self,
        ticker: str,
        key: str,
    ) -> Any | None:
        """Read evidence from distributed blackboard."""
        cache_key = f"{ticker}:{key}"

        if cache_key in self._local_cache:
            return self._local_cache[cache_key].value

        if self._redis:
            try:
                redis_key = self._make_key(ticker, key)
                data = await self._redis.get(redis_key)

                if data:
                    parsed = json.loads(data)
                    evidence = DistributedEvidence(
                        key=parsed["key"],
                        value=parsed["value"],
                        evidence_type=parsed.get("evidence_type", "other"),
                        strength=parsed.get("strength", "medium"),
                        source_agent=parsed.get("source_agent", "unknown"),
                        timestamp=datetime.fromisoformat(parsed["timestamp"]),
                    )
                    self._local_cache[cache_key] = evidence
                    return evidence.value
            except Exception as e:
                logger.error(f"Failed to read from Redis: {e}")

        return None

    async def get_all_evidence(
        self,
        ticker: str,
    ) -> dict[str, Any]:
        """Get all evidence for a ticker."""
        result = {}

        for key, evidence in self._local_cache.items():
            if key.startswith(f"{ticker}:"):
                result[evidence.key] = evidence.value

        if self._redis:
            try:
                pattern = f"{self._namespace}:{ticker}:*"
                keys = []
                async for key in self._redis.scan_iter(match=pattern):
                    keys.append(key)

                for redis_key in keys:
                    data = await self._redis.get(redis_key)
                    if data:
                        parsed = json.loads(data)
                        _, key = self._parse_key(redis_key)
                        result[key] = parsed["value"]
            except Exception as e:
                logger.error(f"Failed to scan Redis: {e}")

        return result

    async def clear_evidence(
        self,
        ticker: str,
        key: str | None = None,
    ) -> None:
        """Clear evidence for a ticker."""
        if key:
            cache_key = f"{ticker}:{key}"
            if cache_key in self._local_cache:
                del self._local_cache[cache_key]

            if self._redis:
                try:
                    redis_key = self._make_key(ticker, key)
                    await self._redis.delete(redis_key)
                except Exception as e:
                    logger.error(f"Failed to delete from Redis: {e}")  # noqa: S608 — logger call, not SQL
        else:
            keys_to_delete = [k for k in self._local_cache.keys() if k.startswith(f"{ticker}:")]
            for k in keys_to_delete:
                del self._local_cache[k]

            if self._redis:
                try:
                    pattern = f"{self._namespace}:{ticker}:*"
                    async for key in self._redis.scan_iter(match=pattern):
                        await self._redis.delete(key)
                except Exception as e:
                    logger.error(f"Failed to clear from Redis: {e}")

    async def exists(self, ticker: str, key: str) -> bool:
        """Check if evidence exists."""
        cache_key = f"{ticker}:{key}"
        if cache_key in self._local_cache:
            return True

        if self._redis:
            try:
                redis_key = self._make_key(ticker, key)
                return await self._redis.exists(redis_key)
            except Exception as e:
                logger.warning("distributed_blackboard.py.exists: %s", e)

        return False

    async def get_evidence_metadata(
        self,
        ticker: str,
        key: str,
    ) -> dict[str, Any] | None:
        """Get metadata for evidence."""
        cache_key = f"{ticker}:{key}"

        if cache_key in self._local_cache:
            evidence = self._local_cache[cache_key]
            return {
                "evidence_type": evidence.evidence_type,
                "strength": evidence.strength,
                "source_agent": evidence.source_agent,
                "timestamp": evidence.timestamp.isoformat(),
            }

        return None


class DistributedBlackboardFactory:
    """Factory for creating distributed blackboard instances."""

    _instance: RedisEvidenceBlackboard | None = None

    @classmethod
    def get_instance(
        cls,
        redis_client: Any = None,
    ) -> RedisEvidenceBlackboard:
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = RedisEvidenceBlackboard(redis_client)
        return cls._instance

    @classmethod
    def set_instance(cls, instance: RedisEvidenceBlackboard) -> None:
        """Set singleton instance."""
        cls._instance = instance


def create_distributed_blackboard(
    redis_client: Any,
    namespace: str = "blackboard",
) -> RedisEvidenceBlackboard:
    """Factory to create distributed blackboard."""
    return RedisEvidenceBlackboard(redis_client, namespace)
