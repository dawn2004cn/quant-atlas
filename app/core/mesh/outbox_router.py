
"""Auto-router: domain events -> transactional outbox.

Ensures critical domain events are automatically written to the
outbox for reliable delivery using the existing EventBus + Outbox.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_outbox_publisher: Any = None


def init_outbox_router(event_bus=None, outbox_service=None, outbox_repo=None):
    """Initialize outbox routing for critical domain events."""
    global _outbox_publisher
    if outbox_service and hasattr(outbox_service, "_outbox_repo"):
        from app.infrastructure.outbox_service import OutboxPublisher
        _outbox_publisher = OutboxPublisher(outbox_service._outbox_repo)
    elif outbox_repo:
        from app.infrastructure.outbox_service import OutboxPublisher
        _outbox_publisher = OutboxPublisher(outbox_repo)

    if _outbox_publisher is None:
        logger.info("Outbox router: no publisher, events will not be persisted")
        return

    _wire_handlers(event_bus)
    logger.info("Outbox router initialized: domain events routed through outbox")


def _wire_handlers(event_bus):
    """Subscribe EventBus signals to outbox persistence."""
    try:
        from app.core.events import factor_research_completed, market_data_synced, risk_alert_triggered

        market_data_synced.connect(_on_market_data_synced, weak=False)
        risk_alert_triggered.connect(_on_risk_alert, weak=False)
        factor_research_completed.connect(_on_factor_completed, weak=False)
        logger.info("Outbox: wired 3 blinker event handlers")
    except Exception as exc:
        logger.debug("Outbox blinker wiring skipped: %s", exc)

    if event_bus is not None:
        try:
            event_bus.subscribe("outbox_router", _on_event_bus_event)
            logger.info("Outbox: subscribed to EventBus")
        except Exception as exc:
            logger.debug("Outbox EventBus subscription skipped: %s", exc)


def _publish(aggregate_type: str, event_type: str, payload: dict[str, Any]):
    global _outbox_publisher
    if _outbox_publisher is None:
        return
    import asyncio
    try:
        asyncio.create_task(
            _outbox_publisher.publish(aggregate_type, aggregate_type + "." + event_type,
                                      "evt_" + str(hash(str(payload))), payload)
        )
    except RuntimeError:
        pass  # no running event loop


def _on_market_data_synced(sender, **kwargs):
    _publish("market_data", "synced", dict(kwargs))


def _on_risk_alert(sender, **kwargs):
    _publish("risk", "alert", dict(kwargs))


def _on_factor_completed(sender, **kwargs):
    _publish("factor", "research_completed", dict(kwargs))


def _on_event_bus_event(event_name: str, payload: dict[str, Any]):
    _publish("event_bus", event_name, payload)
