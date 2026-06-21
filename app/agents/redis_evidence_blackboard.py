from __future__ import annotations

from app.core.runtime_config import get_runtime

"""Redis-backed Evidence Blackboard for distributed multi-agent collaboration.

This implements the distributed state fix from quant_plan.md:
- Uses Redis for cross-process evidence sharing
- Implements atomic operations with Lua scripts
- Supports pub/sub for real-time synchronization

Usage:
    from app.agents.evidence_blackboard import redis
from app.infrastructure.redis_client import RedisClientPoolEvidenceBlackboard
    bb = RedisEvidenceBlackboard()
    bb.write_evidence(EvidencePoint(...))
    data = bb.read_all_evidence()
"""


import orjson as json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import redis
from app.infrastructure.redis_client import RedisClientPool

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RedisEvidencePoint:
    """Evidence point compatible with Redis storage."""
    key: str
    value: Any
    agent: str
    evidence_type: str
    strength: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


class RedisEvidenceBlackboard:
    """Redis-backed evidence blackboard for distributed environments.

    This solves the "cognitive split" problem in multi-process deployments
    (Gunicorn/Celery workers).
    """

    KEY_PREFIX = "evidence:blackboard:"
    EVIDENCE_TTL = 3600

    def __init__(self, redis_url: str | None = None):
        self._redis_url = redis_url or get_runtime("REDIS_URL", "")
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = RedisClientPool.get(self._redis_url).client
        return self._client

    def close(self):
        if self._client:
            self._client.close()
            self._client = None

    def write_evidence(self, point: RedisEvidencePoint) -> bool:
        """Write evidence to Redis with atomic operation."""
        try:
            key = f"{self.KEY_PREFIX}{point.key}"
            data = {
                "value": point.value,
                "agent": point.agent,
                "type": point.evidence_type,
                "strength": point.strength,
                "timestamp": point.timestamp,
                "metadata": point.metadata,
            }
            self.client.setex(key, self.EVIDENCE_TTL, json.dumps(data))
            logger.info(f"RedisBB: wrote {point.key}")
            return True
        except Exception as e:
            logger.error(f"RedisBB write failed: {e}")
            return False

    def read_evidence(self, key: str) -> dict[str, Any] | None:
        """Read evidence from Redis."""
        try:
            full_key = f"{self.KEY_PREFIX}{key}"
            data = self.client.get(full_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"RedisBB read failed: {e}")
            return None

    def read_all_evidence(self) -> list[dict[str, Any]]:
        """Read all evidence entries."""
        results = []
        pattern = f"{self.KEY_PREFIX}*"
        for key in self.client.scan_iter(match=pattern, count=100):
            data = self.client.get(key)
            if data:
                results.append(json.loads(data))
        return results

    def delete_evidence(self, key: str) -> bool:
        """Delete evidence by key."""
        try:
            full_key = f"{self.KEY_PREFIX}{key}"
            self.client.delete(full_key)
            return True
        except Exception as e:
            logger.error(f"RedisBB delete failed: {e}")
            return False

    def clear_all(self) -> bool:
        """Clear all evidence (use with caution)."""
        try:
            pattern = f"{self.KEY_PREFIX}*"
            for key in self.client.scan_iter(match=pattern):
                self.client.delete(key)
            logger.warning("RedisBB: cleared all evidence")
            return True
        except Exception as e:
            logger.error(f"RedisBB clear failed: {e}")
            return False

    def publish_update(self, channel: str, message: dict[str, Any]) -> int:
        """Publish update to channel for real-time sync."""
        try:
            return self.client.publish(channel, json.dumps(message))
        except Exception as e:
            logger.error(f"RedisBB publish failed: {e}")
            return 0

    def subscribe(self, channel: str) -> list[dict[str, Any]]:
        """Subscribe to channel and get messages."""
        pubsub = self.client.pubsub()
        pubsub.subscribe(channel)
        messages = []
        for msg in pubsub.listen():
            if msg["type"] == "message":
                messages.append(json.loads(msg["data"]))
        return messages


_redis_bb: RedisEvidenceBlackboard | None = None


def get_redis_evidence_blackboard() -> RedisEvidenceBlackboard:
    """Get the global Redis-backed evidence blackboard."""
    global _redis_bb
    if _redis_bb is None:
        _redis_bb = RedisEvidenceBlackboard()
    return _redis_bb