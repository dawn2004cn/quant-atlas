from __future__ import annotations
"""Event API Blueprint.

REST endpoints for domain events.
"""


import logging
from flask import Blueprint, request, jsonify

from app.application.mediator import fetch
from app.application.queries import GetEventHistoryQuery


from app.core.logger import get_logger

logger = get_logger(__name__)

event_bp = Blueprint("events", __name__, url_prefix="/api/events")


@event_bp.route("/history", methods=["GET"])
def get_event_history():
    """Get event history."""
    aggregate_id = request.args.get("aggregate_id")
    limit = int(request.args.get("limit", 100))
    
    result = fetch(GetEventHistoryQuery(
        aggregate_id=aggregate_id,
        limit=limit,
    ))
    
    return jsonify(result)


@event_bp.route("/history/<aggregate_id>", methods=["GET"])
def get_aggregate_events(aggregate_id):
    """Get events for specific aggregate."""
    limit = int(request.args.get("limit", 100))
    
    result = fetch(GetEventHistoryQuery(
        aggregate_id=aggregate_id,
        limit=limit,
    ))
    
    return jsonify(result)


@event_bp.route("/replay/<aggregate_id>", methods=["POST"])
def replay_events(aggregate_id):
    """Replay events for aggregate.
    
    Note: This is a placeholder for actual event replay functionality.
    """
    return jsonify({
        "status": "not_implemented",
        "aggregate_id": aggregate_id,
        "message": "Event replay functionality not yet implemented",
    })


@event_bp.route("/publish", methods=["POST"])
def publish_test_event():
    """Publish a test event."""
    data = request.get_json() or {}
    
    from app.application.event_publisher import get_event_publisher
    publisher = get_event_publisher()
    
    event_type = data.get("event_type", "StockCreatedEvent")
    stock_code = data.get("stock_code", "TEST001")
    
    if event_type == "StockCreatedEvent":
        from app.domain.events.handlers import StockCreatedEvent
        publisher.publish_stock_created(
            stock_code=stock_code,
            name=data.get("name", "Test Stock"),
            market=data.get("market", "A"),
        )
    elif event_type == "SignalGeneratedEvent":
        publisher.publish_signal_generated(
            stock_code=stock_code,
            signal_type=data.get("signal_type", "buy"),
            confidence=data.get("confidence", 0.8),
            source=data.get("source", "api"),
        )
    
    return jsonify({
        "status": "published",
        "event_type": event_type,
        "stock_code": stock_code,
    })


__all__ = ["event_bp"]