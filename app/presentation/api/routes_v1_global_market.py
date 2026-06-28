from __future__ import annotations
"""Global market data API routes."""


from flask import Blueprint, request
from flask_login import login_required

from ...core.logger import get_logger
from ...core.registry import register_routes
from ...application.errors import ExternalServiceError, ValidationError
from .common import ok_response, parse_market
from .route_deps import MarketRouteDeps, build_market_route_deps
from .v1_context import ApiV1Context
from ...domain.dto import GlobalQuoteDTO, GlobalHistoryDTO



logger = get_logger(__name__)


@register_routes(name="global_market", context="market_data", description="Global market data API")
def register_global_market_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context | None = None,
    *,
    deps: MarketRouteDeps | None = None,
) -> None:
    route_deps = deps or build_market_route_deps(ctx)
    global_market_service = route_deps.global_market_service
    enable_legacy_response_fields = route_deps.enable_legacy_response_fields

    @blueprint.get("/global/quote")
    @login_required
    def get_global_quote():
        symbol = request.args.get("symbol", "").strip().upper()
        market = request.args.get("market", "US").strip().upper()

        if not symbol:
            raise ValidationError("symbol_required")

        if not global_market_service:
            raise ValidationError("global_market_service_unavailable")

        try:
            m = parse_market(market)
            quote: GlobalQuoteDTO = global_market_service.get_global_quote(symbol, m)

            return ok_response(
                data=quote.model_dump(),
                legacy_alias_key="quote",
                enable_legacy_alias=True,
            )
        except ValidationError:
            raise
        except Exception as exc:
            logger.error("global_quote error: %s %s - %s", symbol, market, exc)
            raise ExternalServiceError(
                "global_quote_failed",
                details={"symbol": symbol, "market": market, "reason": str(exc)},
            ) from exc

    @blueprint.get("/global/history")
    @login_required
    def get_global_history():
        symbol = request.args.get("symbol", "").strip().upper()
        market = request.args.get("market", "US").strip().upper()
        days = int(request.args.get("days", 30))

        if not symbol:
            raise ValidationError("symbol_required")

        if not global_market_service:
            raise ValidationError("global_market_service_unavailable")

        try:
            m = parse_market(market)
            history: GlobalHistoryDTO = global_market_service.get_global_history(
                symbol, m, days=days
            )

            return ok_response(
                data=history.model_dump(),
                legacy_alias_key=None,
                enable_legacy_alias=enable_legacy_response_fields,
            )
        except ValidationError:
            raise
        except Exception as exc:
            logger.error("global_history error: %s %s - %s", symbol, market, exc)
            raise ExternalServiceError(
                "global_history_failed",
                details={"symbol": symbol, "market": market, "reason": str(exc)},
            ) from exc
