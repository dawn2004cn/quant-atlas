from __future__ import annotations
"""Celery tasks for async event processing.

Deprecated — replaced by core/event_bus.py dataclass events + bridge.
Kept for backward compatibility; consumers should migrate to
``app.core.event_bus.emit_trade_executed`` etc.
"""



from ..celery_app import celery_app
from app.core.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name="app.tasks.event_tasks.process_domain_event")
def process_domain_event(
    self,
    event_type: str,
    payload: dict,
    source: str = "system",
    correlation_id: str | None = None,
) -> dict:
    """Process domain event asynchronously via Celery.

    .. deprecated:: Use core/event_bus.py convenience helpers instead.
    """
    logger.info("Processing event: %s from %s", event_type, source)

    try:
        handler = get_event_handler(event_type)
        if handler:
            result = handler(payload)
            logger.info("Event %s processed successfully", event_type)
            return {"status": "success", "result": result}
        else:
            logger.warning("No handler for event type: %s", event_type)
            return {"status": "no_handler", "event_type": event_type}

    except Exception as e:
        logger.error("Failed to process event %s: %s", event_type, e)
        return {"status": "error", "error": str(e)}


def get_event_handler(event_type: str):
    """Get the appropriate handler for the event type.

    Returns None for unmapped types — callers should migrate to
    core/event_bus.py dataclass events.
    """
    handlers = {
        "signal_triggered": handle_signal_triggered,
        "trading_order_placed": handle_order_placed,
        "trading_order_filled": handle_order_filled,
        "backtest_completed": handle_backtest_completed,
        "ai_analysis_completed": handle_ai_analysis_completed,
        "alert_generated": handle_alert_generated,
    }
    return handlers.get(event_type)


def handle_signal_triggered(payload: dict) -> dict:
    """Handle signal triggered event."""
    symbol = payload.get("symbol")
    signal_type = payload.get("signal_type")
    strength = payload.get("strength", 0)

    logger.info(f"Signal triggered: {symbol} {signal_type} strength={strength}")

    return {
        "symbol": symbol,
        "signal_type": signal_type,
        "status": "recorded",
    }


def handle_order_placed(payload: dict) -> dict:
    """Handle order placed event."""
    order_id = payload.get("order_id")
    symbol = payload.get("symbol")
    direction = payload.get("direction")

    logger.info(f"Order placed: {order_id} {direction} {symbol}")

    return {
        "order_id": order_id,
        "status": "accepted",
    }


def handle_order_filled(payload: dict) -> dict:
    """Handle order filled event."""
    order_id = payload.get("order_id")
    symbol = payload.get("symbol")
    filled_price = payload.get("filled_price")
    filled_quantity = payload.get("filled_quantity")

    logger.info(f"Order filled: {order_id} {symbol} @ {filled_price} x {filled_quantity}")

    return {
        "order_id": order_id,
        "status": "filled",
        "value": filled_price * filled_quantity,
    }


def handle_backtest_completed(payload: dict) -> dict:
    """Handle backtest completed event."""
    strategy_name = payload.get("strategy_name")
    metrics = payload.get("metrics", {})

    logger.info(f"Backtest completed: {strategy_name}")

    return {
        "strategy_name": strategy_name,
        "total_return": metrics.get("total_return"),
        "sharpe_ratio": metrics.get("sharpe_ratio"),
    }


def handle_ai_analysis_completed(payload: dict) -> dict:
    """Handle AI analysis completed event."""
    symbol = payload.get("symbol")
    analysis_type = payload.get("analysis_type")

    logger.info(f"AI analysis completed: {symbol} {analysis_type}")

    return {
        "symbol": symbol,
        "status": "completed",
    }


def handle_alert_generated(payload: dict) -> dict:
    """Handle alert generated event."""
    alert_type = payload.get("alert_type")
    severity = payload.get("severity")

    logger.info(f"Alert generated: {alert_type} severity={severity}")

    return {
        "alert_type": alert_type,
        "status": "notification_sent",
    }


# ── Cache Invalidation Events ────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="app.tasks.event_tasks.process_cache_invalidation",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,
)
def process_cache_invalidation(self, event_payload: dict) -> dict:
    """Consume a CacheInvalidationEvent and purge affected cache entries."""
    from app.domain.events.cache_invalidation import CacheInvalidationEvent

    event = CacheInvalidationEvent.from_payload(event_payload)
    logger.info(
        "Processing cache invalidation: ns=%s agg=%s/%s reason=%s",
        event.namespace,
        event.aggregate_type,
        event.aggregate_id,
        event.reason,
    )

    # Purge via the cache port
    try:
        from app.bootstrap_components.providers import create_cache_port
        cache = create_cache_port()
    except Exception:
        logger.warning("No cache port available for invalidation of %s", event.namespace)
        return {"status": "skipped", "reason": "no_cache"}

    for key in event.invalidated_keys:
        cache.delete(key)
    if event.namespace not in [k.split(":")[0] + ":" for k in event.invalidated_keys]:
        try:
            cache.invalidate_prefix(event.namespace)
        except Exception:
            logger.warning("Namespace purge failed for %s", event.namespace)

    return {
        "status": "processed",
        "namespace": event.namespace,
        "keys_purged": len(event.invalidated_keys),
    }
