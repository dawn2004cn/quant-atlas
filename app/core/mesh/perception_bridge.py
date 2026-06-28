"""Perception Bridge — connects CollectivePerceptionLayer to mesh transport (10.0)."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.mesh.perception_layer import (
    CollectivePerceptionLayer,
    PerceptionVector,
    configure_perception_layer,
    get_perception_layer,
)

logger = logging.getLogger(__name__)

_bridge_started = False


def start_perception_bridge(
    *,
    node_id: str = "local",
    region: str = "CN",
    redis_client: Any | None = None,
    embedding_dimensions: int = 64,
) -> CollectivePerceptionLayer | None:
    """Initialize and start the perception layer bridge.

    This sets up the CollectivePerceptionLayer and subscribes to Redis
    perception channels for cross-node resonance.

    Args:
        node_id: This node's identifier
        region: This node's region (CN/US/HK/EU)
        redis_client: Redis client for cross-process sharing
        embedding_dimensions: Dimensionality of embedding vectors

    Returns:
        The initialized CollectivePerceptionLayer, or None on failure
    """
    global _bridge_started

    if _bridge_started:
        return get_perception_layer()

    try:
        layer = CollectivePerceptionLayer(
            node_id=node_id,
            region=region,
            embedding_dimensions=embedding_dimensions,
            redis_client=redis_client,
        )
        configure_perception_layer(layer)

        if redis_client is not None:
            _start_redis_listener(layer, redis_client, region)

        _bridge_started = True
        logger.info(
            "perception bridge active node=%s region=%s dims=%d",
            node_id, region, embedding_dimensions,
        )
        return layer

    except Exception as exc:
        logger.warning("perception bridge failed: %s", exc)
        return None


def stop_perception_bridge() -> None:
    """Stop the perception bridge."""
    global _bridge_started
    configure_perception_layer(None)
    _bridge_started = False


def _start_redis_listener(
    layer: CollectivePerceptionLayer,
    redis_client: Any,
    region: str,
) -> None:
    """Start a background thread listening for cross-node perception vectors."""
    import threading

    channel = f"quant.perception.{region}"

    def _listen() -> None:
        try:
            sub_redis = redis_client.pubsub(ignore_subscribe_messages=True)
            sub_redis.subscribe(channel)
            logger.debug("perception redis listener on %s", channel)

            while True:
                msg = sub_redis.get_message(timeout=1.0)
                if not msg or msg.get("type") != "message":
                    continue
                raw = msg.get("data")
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", errors="replace")
                try:
                    data = json.loads(raw)
                    vector = PerceptionVector.from_dict(data)
                    if vector.origin_node != layer.node_id:
                        layer._check_resonance(vector)
                        with layer._lock:
                            layer._vectors[vector.signal_id] = vector
                except Exception as exc:
                    logger.debug("perception redis parse: %s", exc)

        except Exception as exc:
            logger.warning("perception redis listener stopped: %s", exc)

    thread = threading.Thread(
        target=_listen,
        name="perception-redis-listener",
        daemon=True,
    )
    thread.start()


def publish_perception(
    *,
    text: str | None = None,
    embedding: list[float] | None = None,
    metadata: dict[str, Any] | None = None,
    ttl_seconds: int = 300,
) -> dict[str, Any]:
    """Convenience function to publish a perception vector.

    Args:
        text: Text description of the perception
        embedding: Pre-computed embedding
        metadata: Additional context
        ttl_seconds: Time-to-live

    Returns:
        Published vector dict, or error dict
    """
    layer = get_perception_layer()
    if layer is None:
        return {"ok": False, "error": "perception_layer_not_initialized"}

    try:
        vector = layer.publish(
            text=text,
            embedding=embedding,
            metadata=metadata,
            ttl_seconds=ttl_seconds,
        )
        return {"ok": True, "vector": vector.to_dict()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def subscribe_perception(
    *,
    text: str | None = None,
    embedding: list[float] | None = None,
    threshold: float = 0.7,
    callback: Any | None = None,
    label: str = "",
) -> dict[str, Any]:
    """Convenience function to subscribe to perception resonance.

    Args:
        text: What to watch for
        embedding: Pre-computed embedding
        threshold: Minimum similarity
        callback: Resonance callback
        label: Human-readable label

    Returns:
        Subscription info dict, or error dict
    """
    layer = get_perception_layer()
    if layer is None:
        return {"ok": False, "error": "perception_layer_not_initialized"}

    try:
        sub = layer.subscribe(
            text=text,
            embedding=embedding,
            threshold=threshold,
            callback=callback,
            label=label,
        )
        return {
            "ok": True,
            "subscription": {
                "label": sub.label,
                "threshold": sub.threshold,
                "subscriber_node": sub.subscriber_node,
            },
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


__all__ = [
    "start_perception_bridge",
    "stop_perception_bridge",
    "publish_perception",
    "subscribe_perception",
]
