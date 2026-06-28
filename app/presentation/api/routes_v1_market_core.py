from __future__ import annotations
"""Market / pool HTTP adapters (extracted from monolithic routes.py)."""

from flask import Blueprint, request
from flask_login import login_required

from ...core.logger import get_logger
from ...core.registry import register_routes
from app.modules.system.services.ui.data_freshness_service import enrich_market_payload

from .decorators import service_fallback
from .common import ok_resource, ok_response, parse_market
from .request_parsers import parse_int_param
from .v1_context import ApiV1Context

logger = get_logger(__name__)


@register_routes(name="market_core", context="market_data", description="Market / pool HTTP adapters")
def register_market_core_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register /markets/* and /pool/* routes on the v1 blueprint."""
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/markets/<market>/panorama")
    @service_fallback("market_service")
    def market_panorama(market: str):
        market_service = getattr(ctx, "market_service", None)
        panorama = market_service.get_panorama(parse_market(market))
        panorama_dict = panorama.model_dump() if hasattr(panorama, "model_dump") else {}
        resource = enrich_market_payload(
            {
                "rankings": {
                    "gainers": panorama_dict.get("gainers", []),
                    "losers": panorama_dict.get("losers", []),
                    "amounts": panorama_dict.get("amounts", []),
                    "turnovers": panorama_dict.get("turnovers", []),
                },
                "summary": panorama_dict.get("summary") or {},
                "sectors": panorama_dict.get("sectors") or [],
                "updated_at": panorama_dict.get("updated_at") or panorama_dict.get("timestamp"),
            },
            source="market_panorama",
        )
        return ok_resource(
            resource=resource,
            resource_key="panorama",
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/markets/<market>/quotes")
    @service_fallback("market_service")
    def market_quotes(market: str):
        market_service = getattr(ctx, "market_service", None)
        symbols = request.args.getlist("symbol")
        limit = parse_int_param(request.args.get("limit"), name="limit", default=6000, min_value=1)
        logger.info("market_quotes called: market=%s, symbols=%s, limit=%s", market, len(symbols), limit)
        quotes = market_service.list_quotes(parse_market(market), symbols or None)
        if limit and limit > 0 and len(quotes) > limit:
            quotes = quotes[:limit]
        return ok_response(
            data={"stocks": quotes, "count": len(quotes)},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/pool/<market>/live")
    @login_required
    @service_fallback("pool_service")
    def live_pool(market: str):
        pool_service = getattr(ctx, "pool_service", None)
        top_n = parse_int_param(request.args.get("top_n"), name="top_n", default=20, min_value=1)
        payload = pool_service.get_live_pool(parse_market(market), top_n=top_n)
        return ok_resource(
            resource=payload,
            resource_key="pool",
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/markets/<market>/movements")
    @service_fallback("market_service")
    def market_movements(market: str):
        market_service = getattr(ctx, "market_service", None)
        movements = market_service.get_movements(parse_market(market), top_n=12)
        return ok_response(
            data={"movements": movements},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    # ── Legacy compatibility aliases ──────────────────────────────────
    # These mirror the old /api/market/* paths from scripts/web_app.py
    # so frontend code that hasn't been migrated continues to work.

    @blueprint.get("/market/sentiment")
    @service_fallback("market_service")
    def market_sentiment_legacy():
        """Legacy alias for /api/v1/markets/<market>/sentiment (defaults to CN)."""
        return market_sentiment("CN")

    @blueprint.get("/market/movements")
    @service_fallback("market_service")
    def market_movements_legacy():
        """Legacy alias for /api/v1/markets/<market>/movements (defaults to CN)."""
        return market_movements("CN")

    @blueprint.get("/market-rankings")
    @login_required
    @service_fallback("market_service")
    def market_rankings_legacy():
        """Legacy alias for /api/v1/markets/CN/panorama (rankings subset)."""
        market_service = getattr(ctx, "market_service", None)
        panorama = market_service.get_panorama(parse_market("CN"))
        panorama_dict = panorama.model_dump() if hasattr(panorama, "model_dump") else {}
        return ok_response(
            data={
                "rankings": {
                    "gainers": panorama_dict.get("gainers", []),
                    "losers": panorama_dict.get("losers", []),
                    "amounts": panorama_dict.get("amounts", []),
                    "turnovers": panorama_dict.get("turnovers", []),
                },
                "summary": panorama_dict.get("summary") or {},
                "sectors": panorama_dict.get("sectors") or [],
                "updated_at": panorama_dict.get("updated_at") or panorama_dict.get("timestamp"),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/markets/<market>/sentiment")
    @service_fallback("market_service")
    def market_sentiment(market: str):
        market_service = getattr(ctx, "market_service", None)
        payload = market_service.get_sentiment(parse_market(market))
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/markets/<market>/headlines")
    @login_required
    @service_fallback("news_provider")
    def market_portal_headlines(market: str):
        news_provider = getattr(ctx, "news_provider", None)
        m = parse_market(market)
        limit = parse_int_param(request.args.get("limit"), name="limit", default=40, min_value=1)
        limit = min(limit, 100)
        items = news_provider.get_market_headlines(m, limit=limit)
        serial = [
            {
                "title": it.title,
                "published_at": it.published_at,
                "source": it.source,
                "url": it.url,
                "summary": it.summary,
            }
            for it in items
        ]
        try:
            from app.modules.strategy.services.analytics.headline_signal_enrichment_service import (
                HeadlineSignalEnrichmentService,
            )

            serial = HeadlineSignalEnrichmentService().enrich_headlines(serial, market=m.value)
        except Exception:
            logger.warning("headline enrichment skipped")
        return ok_response(
            data={"headlines": serial},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
            market=m.value,
            count=len(serial),
        )
