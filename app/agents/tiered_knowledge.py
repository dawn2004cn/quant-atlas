from __future__ import annotations
"""Tiered Knowledge System - Cold-Hot Data Separation.

This module implements Multi-level Knowledge Tiering from midify_plan11.md:
- Hot Tier: In-memory cache for fast access (existing blackboard)
- Cold Tier: Redis for distributed blackboard (long-running tasks like 10-year backtest)
- Semantic Deduplication: RAG-based conclusion caching

Usage:
    tiered_knowledge = TieredKnowledgeSystem()
    result = tiered_knowledge.get_or_fetch(key, fetch_func)
    tiered_knowledge.sync_to_cold_tier(key, data)
"""


import orjson as json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from collections.abc import Callable
from app.core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class TieredData:
    """Data stored across tiers."""
    key: str
    value: Any
    tier: str
    created_at: datetime
    last_accessed: datetime
    ttl_seconds: int
    semantic_signature: str | None = None


class TieredKnowledgeSystem:
    """Multi-level knowledge tiering system.

    Hot Tier (Memory): Fast access, short TTL
    Cold Tier (Redis): Distributed, long TTL, persists across sessions
    """

    def __init__(
        self,
        redis_client: Any = None,
        hot_ttl_seconds: int = 300,
        cold_ttl_seconds: int = 86400 * 7,
    ):
        self._redis = redis_client
        self._hot_cache: dict[str, TieredData] = {}
        self._hot_ttl = hot_ttl_seconds
        self._cold_ttl = cold_ttl_seconds

    async def get_or_fetch(
        self,
        key: str,
        fetch_func: Callable[[], Any],
        prefer_hot: bool = True,
    ) -> Any:
        """Get data from cache or fetch from source."""
        if prefer_hot:
            hot_result = self._get_from_hot_tier(key)
            if hot_result is not None:
                return hot_result

            cold_result = await self._get_from_cold_tier(key)
            if cold_result is not None:
                self._put_to_hot_tier(key, cold_result)
                return cold_result

        result = await fetch_func()

        if result:
            await self._put_to_cold_tier(key, result)
            self._put_to_hot_tier(key, result)

        return result

    def _get_from_hot_tier(self, key: str) -> Any | None:
        """Get from hot tier (memory)."""
        if key in self._hot_cache:
            data = self._hot_cache[key]

            if self._is_expired(data):
                del self._hot_cache[key]
                return None

            data.last_accessed = datetime.now()
            return data.value

        return None

    async def _get_from_cold_tier(self, key: str) -> Any | None:
        """Get from cold tier (Redis)."""
        if not self._redis:
            return None

        try:
            redis_key = f"blackboard:{key}"
            value = await self._redis.get(redis_key)

            if value:
                return json.loads(value)
        except Exception as e:
            logger.warning(f"Failed to get from cold tier: {e}")

        return None

    def _put_to_hot_tier(self, key: str, value: Any) -> None:
        """Put data into hot tier."""
        self._hot_cache[key] = TieredData(
            key=key,
            value=value,
            tier="hot",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            ttl_seconds=self._hot_ttl,
        )

        self._cleanup_hot_tier()

    async def _put_to_cold_tier(self, key: str, value: Any) -> None:
        """Put data into cold tier (Redis)."""
        if not self._redis:
            return

        try:
            redis_key = f"blackboard:{key}"
            serialized = json.dumps(value, default=str)
            await self._redis.setex(redis_key, self._cold_ttl, serialized)
        except Exception as e:
            logger.warning(f"Failed to put to cold tier: {e}")

    def _is_expired(self, data: TieredData) -> bool:
        """Check if data is expired."""
        age = (datetime.now() - data.created_at).total_seconds()
        return age > data.ttl_seconds

    def _cleanup_hot_tier(self) -> None:
        """Clean up expired entries from hot tier."""
        expired_keys = [
            k for k, v in self._hot_cache.items()
            if self._is_expired(v)
        ]
        for key in expired_keys:
            del self._hot_cache[key]

    async def sync_to_cold_tier(self, key: str, data: Any) -> None:
        """Manually sync specific data to cold tier."""
        await self._put_to_cold_tier(key, data)

    async def restore_from_cold_tier(self, key: str) -> Any | None:
        """Restore data from cold tier to hot tier."""
        result = await self._get_from_cold_tier(key)
        if result:
            self._put_to_hot_tier(key, result)
        return result


class SemanticDeduplicator:
    """Semantic deduplication using RAG-like similarity matching.

    Prevents redundant tool calls by checking if semantically similar
    conclusions already exist in blackboard.
    """

    def __init__(self, similarity_threshold: float = 0.85):
        self._similarity_threshold = similarity_threshold
        self._conclusion_store: list[dict[str, Any]] = []

    def check_semantic_duplicate(
        self,
        new_conclusion: str,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Check if semantically similar conclusion exists."""
        new_signature = self._create_signature(new_conclusion, context)

        for stored in self._conclusion_store:
            similarity = self._calculate_similarity(new_signature, stored["signature"])

            if similarity >= self._similarity_threshold:
                return {
                    "is_duplicate": True,
                    "stored_conclusion": stored["conclusion"],
                    "similarity": similarity,
                    "stored_key": stored["key"],
                }

        return None

    def store_conclusion(
        self,
        key: str,
        conclusion: str,
        context: dict[str, Any],
    ) -> None:
        """Store conclusion for future deduplication."""
        signature = self._create_signature(conclusion, context)

        self._conclusion_store.append({
            "key": key,
            "conclusion": conclusion,
            "signature": signature,
            "context": context,
            "timestamp": datetime.now(),
        })

        if len(self._conclusion_store) > 1000:
            self._conclusion_store = self._conclusion_store[-1000:]

    def _create_signature(
        self,
        conclusion: str,
        context: dict[str, Any],
    ) -> str:
        """Create semantic signature for conclusion."""
        key_elements = [
            conclusion.lower()[:50],
            context.get("ticker", ""),
            context.get("agent_type", ""),
            str(sorted(context.get("indicators", {}).keys())[:5]),
        ]
        return "|".join(key_elements)

    def _calculate_similarity(self, sig1: str, sig2: str) -> float:
        """Calculate simple similarity between signatures."""
        words1 = set(sig1.split("|"))
        words2 = set(sig2.split("|"))

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0


class EvidenceAwareToolWrapperV2:
    """Enhanced tool wrapper with tiered knowledge and semantic dedup."""

    def __init__(
        self,
        tool_func: Callable,
        tool_name: str,
        tiered_system: TieredKnowledgeSystem | None = None,
        deduplicator: SemanticDeduplicator | None = None,
    ):
        self._tool = tool_func
        self._tool_name = tool_name
        self._tiered = tiered_system or TieredKnowledgeSystem()
        self._dedup = deduplicator or SemanticDeduplicator()

    async def execute(
        self,
        agent_name: str,
        context: dict[str, Any],
        **kwargs,
    ) -> Any:
        """Execute tool with tiered caching and deduplication."""
        key = self._build_cache_key(self._tool_name, kwargs)

        dup_result = self._dedup.check_semantic_duplicate(
            context.get("conclusion", ""),
            context,
        )
        if dup_result:
            logger.info(f"Semantic duplicate found: {dup_result['stored_key']}")
            return {
                "from_cache": True,
                "cached_conclusion": dup_result["stored_conclusion"],
                "similarity": dup_result["similarity"],
            }

        result = await self._tiered.get_or_fetch(
            key,
            lambda: self._tool(**kwargs),
        )

        if context.get("conclusion"):
            self._dedup.store_conclusion(
                key,
                context["conclusion"],
                context,
            )

        return result

    def _build_cache_key(self, tool_name: str, args: dict[str, Any]) -> str:
        """Build cache key from tool name and arguments."""
        sorted_args = sorted(args.items())
        args_str = "|".join(f"{k}={v}" for k, v in sorted_args)
        return f"{tool_name}:{args_str}"


def create_tiered_system(redis_client: Any = None) -> TieredKnowledgeSystem:
    """Factory to create tiered knowledge system."""
    return TieredKnowledgeSystem(redis_client)


def create_semantic_deduplicator(threshold: float = 0.85) -> SemanticDeduplicator:
    """Factory to create semantic deduplicator."""
    return SemanticDeduplicator(similarity_threshold=threshold)
