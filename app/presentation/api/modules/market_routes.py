"""Market Routes Module - Example of route modularization.

This module demonstrates how to extract routes into separate modules
while using UseCases for business logic.
"""

from __future__ import annotations

from app.domain.enums import MarketCode
from flask import Blueprint
from flask_login import login_required

from app.application.errors import ValidationError
from app.application.use_cases import UseCaseResult
from app.application.use_cases.comprehensive_factory import UseCaseFactory
from app.presentation.api.common import ok_collection, ok_response
from app.presentation.api.request_parsers import parse_int_param


def _require_success(result: UseCaseResult):
    """Return data or raise ValidationError for use-case failures."""
    if result.success:
        return result.data
    raise ValidationError(
        "market_use_case_failed",
        details={"reason": result.error or "unknown"},
    )


def create_market_routes(use_case_factory: UseCaseFactory) -> Blueprint:
    """Create market routes blueprint."""
    bp = Blueprint("market", __name__, url_prefix="/api/v1/markets")

    @bp.route("/CN/quotes", methods=["GET"])
    @login_required
    def get_quotes():
        """Get stock quotes."""
        symbols = request.args.getlist("symbol")
        limit = parse_int_param(request.args.get("limit"), "limit", 12000, 1)
        use_case = use_case_factory.get_stock_quotes()
        result = use_case.execute(symbols=symbols, market=MarketCode.CN, limit=limit)
        return jsonify(_require_success(result))

    @bp.route("/CN/panorama", methods=["GET"])
    @login_required
    def get_panorama():
        """Get market panorama with rankings."""
        use_case = use_case_factory.get_market_panorama()
        result = use_case.execute(market=MarketCode.CN)
        return ok_response(data=_require_success(result))

    @bp.route("/CN/movements", methods=["GET"])
    @login_required
    def get_movements():
        """Get market movements (up/down counts)."""
        top_n = parse_int_param(request.args.get("top_n"), "top_n", 12, 1)
        use_case = use_case_factory.get_market_movements()
        result = use_case.execute(market=MarketCode.CN, top_n=top_n)
        data = _require_success(result)
        return ok_collection(items=data.get("movements", []), item_key="movements")

    @bp.route("/CN/sentiment", methods=["GET"])
    @login_required
    def get_sentiment():
        """Get market sentiment."""
        use_case = use_case_factory.get_market_sentiment()
        result = use_case.execute(market=MarketCode.CN)
        return ok_response(data=_require_success(result))

    @bp.route("/CN/headlines", methods=["GET"])
    @login_required
    def get_headlines():
        """Get market headlines/news."""
        limit = parse_int_param(request.args.get("limit"), "limit", 40, 1, 100)
        use_case = use_case_factory.get_market_headlines()
        result = use_case.execute(market=MarketCode.CN, limit=limit)
        return ok_response(data=_require_success(result))

    return bp


def register_market_routes(blueprint: Blueprint, **services) -> None:
    """Register market routes to main blueprint."""
    factory = UseCaseFactory(
        market_service=services.get("market_service"),
        stock_service=services.get("stock_service"),
        news_provider=services.get("news_provider"),
    )

    market_bp = create_market_routes(factory)
    blueprint.register_blueprint(market_bp)
