"""Collective Perception Layer — shared embedding space for cross-node async prediction (10.0 Neural Resonance)."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import threading
import time
from datetime import datetime, timezone
from typing import Any
from collections.abc import Callable

logger = logging.getLogger(__name__)


class PerceptionVector:
    """A semantic signal in the shared embedding space.

    Each perception vector represents a distilled insight from a node
    (e.g., "600519 showing head-and-shoulders pattern", "USD/CNY breaking resistance").
    Other nodes can subscribe to related vectors and receive resonance triggers.
    """

    def __init__(
        self,
        *,
        signal_id: str,
        origin_node: str,
        origin_region: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
        timestamp: str | None = None,
        ttl_seconds: int = 300,
    ):
        self.signal_id = signal_id
        self.origin_node = origin_node
        self.origin_region = origin_region
        self.embedding = embedding
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.ttl_seconds = ttl_seconds
        self._created_at = time.monotonic()

    def is_expired(self) -> bool:
        return (time.monotonic() - self._created_at) > self.ttl_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "origin_node": self.origin_node,
            "origin_region": self.origin_region,
            "embedding": self.embedding,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "ttl_seconds": self.ttl_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PerceptionVector:
        return cls(
            signal_id=data["signal_id"],
            origin_node=data["origin_node"],
            origin_region=data["origin_region"],
            embedding=data["embedding"],
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp"),
            ttl_seconds=data.get("ttl_seconds", 300),
        )


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def text_to_embedding(text: str, *, dimensions: int = 64) -> list[float]:
    """Simple deterministic text-to-embedding hash (no LLM dependency).

    For production, replace with a real embedding model. This provides
    a stable, reproducible embedding for semantic matching.
    """
    h = hashlib.sha256(text.encode("utf-8")).digest()
    expanded = (h * ((dimensions * 4 // len(h)) + 1))[:dimensions * 4]
    values = []
    for i in range(0, len(expanded), 4):
        val = int.from_bytes(expanded[i:i+4], "big", signed=True)
        values.append(val / 2147483647.0)
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


class ResonanceSubscription:
    """A node's subscription to a region of the embedding space."""

    def __init__(
        self,
        *,
        subscriber_node: str,
        subscriber_region: str,
        embedding: list[float],
        threshold: float = 0.7,
        callback: Callable[[PerceptionVector, float], None] | None = None,
        label: str = "",
    ):
        self.subscriber_node = subscriber_node
        self.subscriber_region = subscriber_region
        self.embedding = embedding
        self.threshold = threshold
        self.callback = callback
        self.label = label
        self.created_at = datetime.now(timezone.utc).isoformat()


class CollectivePerceptionLayer:
    """Shared embedding space for cross-node async prediction (Neural Resonance).

    Nodes publish perception vectors (distilled insights) and subscribe to
    regions of the embedding space. When a new vector is published, all
    subscriptions with sufficient cosine similarity are triggered, enabling
    millisecond-level cross-domain intelligence propagation.

    Example flow:
    1. Tokyo node detects "JPY breaking support" → publishes perception vector
    2. London node has subscription for "currency risk" (similarity > 0.7)
    3. London node receives resonance trigger → activates GBP arbitrage agent
    """

    def __init__(
        self,
        *,
        node_id: str = "local",
        region: str = "CN",
        embedding_dimensions: int = 64,
        redis_client: Any | None = None,
    ):
        self._node_id = node_id
        self._region = region
        self._dimensions = embedding_dimensions
        self._redis = redis_client
        self._lock = threading.Lock()

        self._vectors: dict[str, PerceptionVector] = {}
        self._subscriptions: list[ResonanceSubscription] = []
        self._resonance_log: list[dict[str, Any]] = []
        self._stats = {
            "published": 0,
            "resonated": 0,
            "expired_cleaned": 0,
        }

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def region(self) -> str:
        return self._region

    def publish(
        self,
        *,
        text: str | None = None,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
        ttl_seconds: int = 300,
    ) -> PerceptionVector:
        """Publish a perception vector to the shared embedding space.

        Args:
            text: Text description (auto-embedded if no embedding provided)
            embedding: Pre-computed embedding vector
            metadata: Additional context (symbol, signal_type, etc.)
            ttl_seconds: Time-to-live for the vector

        Returns:
            The published PerceptionVector
        """
        if embedding is None:
            if text is None:
                raise ValueError("Either text or embedding must be provided")
            embedding = text_to_embedding(text, dimensions=self._dimensions)

        signal_id = hashlib.sha256(
            f"{self._node_id}:{time.time()}:{json.dumps(metadata or {}, sort_keys=True)}".encode()
        ).hexdigest()[:16]

        vector = PerceptionVector(
            signal_id=f"pv-{signal_id}",
            origin_node=self._node_id,
            origin_region=self._region,
            embedding=embedding,
            metadata=metadata or ({"text": text} if text else {}),
            ttl_seconds=ttl_seconds,
        )

        with self._lock:
            self._vectors[vector.signal_id] = vector
            self._stats["published"] += 1

        self._check_resonance(vector)

        if self._redis is not None:
            self._publish_to_redis(vector)

        logger.debug(
            "perception published: %s from %s/%s",
            vector.signal_id, vector.origin_node, vector.origin_region,
        )
        return vector

    def subscribe(
        self,
        *,
        text: str | None = None,
        embedding: list[float] | None = None,
        threshold: float = 0.7,
        callback: Callable[[PerceptionVector, float], None] | None = None,
        label: str = "",
    ) -> ResonanceSubscription:
        """Subscribe to a region of the embedding space.

        Args:
            text: Text description of what to watch for
            embedding: Pre-computed embedding for the subscription
            threshold: Minimum cosine similarity to trigger (0.0-1.0)
            callback: Function called when resonance detected (vector, similarity)
            label: Human-readable label for the subscription

        Returns:
            The created ResonanceSubscription
        """
        if embedding is None:
            if text is None:
                raise ValueError("Either text or embedding must be provided")
            embedding = text_to_embedding(text, dimensions=self._dimensions)

        sub = ResonanceSubscription(
            subscriber_node=self._node_id,
            subscriber_region=self._region,
            embedding=embedding,
            threshold=threshold,
            callback=callback,
            label=label or (text[:50] if text else ""),
        )

        with self._lock:
            self._subscriptions.append(sub)

        logger.debug(
            "perception subscription added: %s (threshold=%.2f, dim=%d)",
            sub.label, threshold, len(embedding),
        )
        return sub

    def unsubscribe(self, subscription: ResonanceSubscription) -> None:
        """Remove a subscription."""
        with self._lock:
            self._subscriptions = [s for s in self._subscriptions if s is not subscription]

    def query(
        self,
        *,
        text: str | None = None,
        embedding: list[float] | None = None,
        top_k: int = 5,
        min_similarity: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Query the embedding space for similar perception vectors.

        Args:
            text: Query text
            embedding: Pre-computed query embedding
            top_k: Maximum results to return
            min_similarity: Minimum cosine similarity threshold

        Returns:
            List of matching vectors with similarity scores
        """
        if embedding is None:
            if text is None:
                raise ValueError("Either text or embedding must be provided")
            embedding = text_to_embedding(text, dimensions=self._dimensions)

        self._cleanup_expired()

        results = []
        with self._lock:
            for vector in self._vectors.values():
                sim = cosine_similarity(embedding, vector.embedding)
                if sim >= min_similarity:
                    results.append({
                        "vector": vector.to_dict(),
                        "similarity": round(sim, 4),
                    })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def _check_resonance(self, vector: PerceptionVector) -> list[dict[str, Any]]:
        """Check all subscriptions for resonance with a new vector."""
        if vector.origin_node == self._node_id:
            return []

        triggered = []
        with self._lock:
            subs = list(self._subscriptions)

        for sub in subs:
            sim = cosine_similarity(vector.embedding, sub.embedding)
            if sim >= sub.threshold:
                resonance_event = {
                    "signal_id": vector.signal_id,
                    "subscriber": sub.subscriber_node,
                    "similarity": round(sim, 4),
                    "label": sub.label,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                triggered.append(resonance_event)

                with self._lock:
                    self._resonance_log.append(resonance_event)
                    if len(self._resonance_log) > 1000:
                        self._resonance_log = self._resonance_log[-500:]
                    self._stats["resonated"] += 1

                if sub.callback is not None:
                    try:
                        sub.callback(vector, sim)
                    except Exception as exc:
                        logger.warning("resonance callback error: %s", exc)

                logger.info(
                    "RESONANCE: %s → %s (sim=%.3f, label=%s)",
                    vector.signal_id, sub.subscriber_node, sim, sub.label,
                )

        return triggered

    def _publish_to_redis(self, vector: PerceptionVector) -> None:
        """Publish vector to Redis for cross-process sharing."""
        if self._redis is None:
            return
        try:
            channel = f"quant.perception.{self._region}"
            payload = json.dumps(vector.to_dict(), ensure_ascii=False)
            self._redis.publish(channel, payload)
        except Exception as exc:
            logger.debug("perception redis publish: %s", exc)

    def _cleanup_expired(self) -> None:
        """Remove expired vectors."""
        with self._lock:
            expired = [k for k, v in self._vectors.items() if v.is_expired()]
            for k in expired:
                del self._vectors[k]
            self._stats["expired_cleaned"] += len(expired)

    def get_manifest(self) -> dict[str, Any]:
        """Get perception layer status."""
        self._cleanup_expired()
        with self._lock:
            return {
                "node_id": self._node_id,
                "region": self._region,
                "embedding_dimensions": self._dimensions,
                "active_vectors": len(self._vectors),
                "subscriptions": len(self._subscriptions),
                "subscription_labels": [s.label for s in self._subscriptions],
                "stats": dict(self._stats),
                "recent_resonance": list(self._resonance_log[-10:]),
            }

    def list_vectors(self, *, limit: int = 50) -> list[dict[str, Any]]:
        """List active perception vectors."""
        self._cleanup_expired()
        with self._lock:
            vectors = list(self._vectors.values())
        vectors.sort(key=lambda v: v.timestamp, reverse=True)
        return [v.to_dict() for v in vectors[:limit]]


_perception_layer: CollectivePerceptionLayer | None = None


def get_perception_layer() -> CollectivePerceptionLayer | None:
    return _perception_layer


def configure_perception_layer(layer: CollectivePerceptionLayer | None) -> None:
    global _perception_layer
    _perception_layer = layer


__all__ = [
    "CollectivePerceptionLayer",
    "PerceptionVector",
    "ResonanceSubscription",
    "cosine_similarity",
    "text_to_embedding",
    "get_perception_layer",
    "configure_perception_layer",
]
