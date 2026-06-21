from __future__ import annotations
"""Domain API Blueprint.

REST endpoints for domain operations using CQRS and aggregates.
"""


import logging
from flask import Blueprint, request, jsonify

from app.application.mediator import send, fetch
from app.application.commands import (
    CreateStockCommand,
    UpdatePositionCommand,
    SubmitOrderCommand,
    ScreenStocksCommand,
    GenerateSignalCommand,
)
from app.application.queries import (
    GetStockQuery,
    GetPortfolioQuery,
    GetOrdersQuery,
    GetSignalsQuery,
)


from app.core.logger import get_logger

logger = get_logger(__name__)

domain_bp = Blueprint("domain", __name__, url_prefix="/api/domain")


@domain_bp.route("/stocks", methods=["POST"])
def create_stock():
    """Create a new stock."""
    data = request.get_json() or {}
    
    result = send(CreateStockCommand(
        stock_code=data.get("stock_code", ""),
        name=data.get("name", ""),
        market=data.get("market", "A"),
    ))
    
    return jsonify(result)


@domain_bp.route("/stocks/<stock_code>", methods=["GET"])
def get_stock(stock_code):
    """Get stock details."""
    result = fetch(GetStockQuery(stock_code=stock_code))
    
    return jsonify(result)


@domain_bp.route("/stocks/screens", methods=["POST"])
def screen_stocks():
    """Screen stocks with criteria."""
    criteria = request.get_json() or {}
    
    result = send(ScreenStocksCommand(criteria=criteria))
    
    return jsonify(result)


@domain_bp.route("/stocks/<stock_code>/signals", methods=["GET"])
def get_signals(stock_code):
    """Get signals for stock."""
    active_only = request.args.get("active_only", "false").lower() == "true"
    
    result = fetch(GetSignalsQuery(
        stock_code=stock_code,
        active_only=active_only,
    ))
    
    return jsonify(result)


@domain_bp.route("/stocks/<stock_code>/signals/generate", methods=["POST"])
def generate_signal(stock_code):
    """Generate signal for stock."""
    indicators = request.get_json() or {}
    
    result = send(GenerateSignalCommand(
        stock_code=stock_code,
        indicators=indicators,
    ))
    
    return jsonify(result)


@domain_bp.route("/portfolio/<portfolio_id>", methods=["GET"])
def get_portfolio(portfolio_id):
    """Get portfolio details."""
    result = fetch(GetPortfolioQuery(portfolio_id=portfolio_id))
    
    return jsonify(result)


@domain_bp.route("/portfolio/<portfolio_id>/positions", methods=["POST"])
def add_position(portfolio_id):
    """Add position to portfolio."""
    data = request.get_json() or {}
    
    result = send(UpdatePositionCommand(
        portfolio_id=portfolio_id,
        stock_code=data.get("stock_code", ""),
        quantity=data.get("quantity", 0),
        price=data.get("price", 0),
        action=data.get("action", "add"),
    ))
    
    return jsonify(result)


@domain_bp.route("/portfolio/<portfolio_id>/orders", methods=["GET"])
def get_orders(portfolio_id):
    """Get orders for portfolio."""
    status = request.args.get("status")
    
    result = fetch(GetOrdersQuery(
        portfolio_id=portfolio_id,
        status=status,
    ))
    
    return jsonify(result)


@domain_bp.route("/portfolio/<portfolio_id>/orders", methods=["POST"])
def submit_order(portfolio_id):
    """Submit an order."""
    data = request.get_json() or {}
    
    result = send(SubmitOrderCommand(
        portfolio_id=portfolio_id,
        stock_code=data.get("stock_code", ""),
        side=data.get("side", "buy"),
        order_type=data.get("order_type", "market"),
        quantity=data.get("quantity", 0),
        price=data.get("price"),
    ))
    
    return jsonify(result)


@domain_bp.route("/aggregate-stats", methods=["GET"])
def get_aggregate_stats():
    """Get aggregate registry stats."""
    from app.application.aggregate_registry import get_aggregate_registry
    
    registry = get_aggregate_registry()
    stats = registry.get_stats()
    
    return jsonify({
        "status": "success",
        "stats": stats,
    })


__all__ = ["domain_bp"]