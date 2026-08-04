from __future__ import annotations

"""Market / pool HTTP adapters (extracted from monolithic routes.py)."""

from flask import Blueprint, request
from flask_login import login_required

from app.modules.system.services.ui.data_freshness_service import enrich_market_payload

from ...core.logger import get_logger
from ...core.registry import register_routes
from ...domain.enums import MarketCode
from .common import ok_resource, ok_response, parse_market
from .decorators import service_fallback
from .request_parsers import parse_int_param
from .v1_context import ApiV1Context
from ...core.middleware.request_context import require_authenticated_user_id

logger = get_logger(__name__)


def _parse_symbol_args(req) -> list[str]:
    """Accept repeated ``symbol=`` / ``symbols=`` or a single comma-separated list."""
    symbols = list(req.args.getlist("symbol") or [])
    symbols.extend(req.args.getlist("symbols") or [])
    if len(symbols) == 1 and ("," in symbols[0] or " " in symbols[0]):
        symbols = [part.strip() for part in symbols[0].replace(",", " ").split() if part.strip()]
    # Flatten accidental comma-joined values in multi-value lists.
    flat: list[str] = []
    for item in symbols:
        if "," in item:
            flat.extend(part.strip() for part in item.split(",") if part.strip())
        elif item.strip():
            flat.append(item.strip())
    return flat


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
        symbols = _parse_symbol_args(request)
        limit = parse_int_param(request.args.get("limit"), name="limit", default=6000, min_value=1)
        mc = parse_market(market)
        logger.info("market_quotes called: market=%s, symbols=%s, limit=%s", market, len(symbols), limit)
        quotes: list = []
        if symbols and mc == MarketCode.CN:
            try:
                from app.modules.market_data.services.cn_quote_snapshot import get_cn_quote_snapshot

                snapshot = get_cn_quote_snapshot()
                hits, missing = snapshot.lookup_rows(symbols)
                quotes = list(hits)
                if missing:
                    extra = market_service.list_quotes(mc, missing) or []
                    quotes.extend(extra)
                elif not quotes:
                    quotes = market_service.list_quotes(mc, symbols) or []
            except Exception as exc:
                logger.debug("CnQuoteSnapshot batch lookup failed: %s", exc)
                quotes = market_service.list_quotes(mc, symbols) or []
        else:
            quotes = market_service.list_quotes(mc, symbols or None) or []
        if limit and limit > 0 and len(quotes) > limit:
            quotes = quotes[:limit]
        if not symbols and mc == MarketCode.CN and quotes:
            try:
                from app.modules.market_data.services.cn_quote_snapshot import get_cn_quote_snapshot

                get_cn_quote_snapshot().load_rows(quotes)
            except Exception as exc:
                logger.debug("CnQuoteSnapshot warm from market_quotes: %s", exc)
        meta_extra: dict = {}
        if not symbols:
            from app.modules.market_data.services.quotes_dump_metrics import record_full_dump

            record_full_dump(market=market, rows=len(quotes))
            preferred = f"/markets/{market}/quotes/page"
            meta_extra["preferred_endpoint"] = preferred
            meta_extra["legacy_full_dump"] = True
            meta_extra["hint"] = (
                "全市场行情请优先使用 quotes/page 分页；"
                "本接口适合显式 symbol(s) 批量查询"
            )
            logger.info(
                "market_quotes full dump preferred_page_endpoint: market=%s count=%s",
                market,
                len(quotes),
            )
        else:
            from app.modules.market_data.services.quotes_dump_metrics import record_symbol_batch

            record_symbol_batch(market=market, symbols=len(symbols))
        resp = ok_response(
            data={"stocks": quotes, "count": len(quotes)},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
            **meta_extra,
        )
        if not symbols:
            # ok_response → (Response, status); attach migration headers for monitors.
            response, status = resp if isinstance(resp, tuple) else (resp, 200)
            preferred_api = f"/api/v1/markets/{market}/quotes/page"
            response.headers["X-Preferred-Endpoint"] = preferred_api
            response.headers["Warning"] = (
                '299 quant-atlas "Full-market /quotes dump is legacy; use quotes/page"'
            )
            link_pref = f'<{preferred_api}>; rel="alternate"'
            existing_link = response.headers.get("Link")
            response.headers["Link"] = (
                f"{existing_link}, {link_pref}" if existing_link else link_pref
            )
            return response, status
        return resp

    @blueprint.get("/markets/<market>/quotes/page")
    @service_fallback("market_service")
    def market_quotes_page(market: str):
        """Paginated market table for panorama UI (single snapshot load per TTL)."""
        mc = parse_market(market)
        if mc != MarketCode.CN:
            return ok_response(
                data={"items": [], "total": 0, "page": 1, "page_size": 40, "stats": {}},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        page = parse_int_param(request.args.get("page"), name="page", default=1, min_value=1)
        page_size = parse_int_param(
            request.args.get("page_size"),
            name="page_size",
            default=40,
            min_value=1,
            max_value=200,
        )
        sort_key = (request.args.get("sort") or "change_pct").strip()
        sort_order = (request.args.get("order") or "desc").strip()
        board_filter = (request.args.get("filter") or "all").strip()
        scope = (request.args.get("scope") or "market").strip().lower()
        symbol_args = _parse_symbol_args(request)
        codes: set[str] | None = None
        if symbol_args:
            codes = {str(s) for s in symbol_args if s}
            scope = "symbols"
        elif scope == "watchlist":
            watchlist_service = getattr(ctx, "watchlist_service", None)
            if watchlist_service is None:
                return ok_response(
                    data={
                        "items": [],
                        "total": 0,
                        "page": page,
                        "page_size": page_size,
                        "stats": {},
                        "scope": "watchlist",
                    },
                    legacy_alias_key=None,
                    enable_legacy_alias=legacy,
                )
            try:
                user_id = require_authenticated_user_id()
                codes = {str(s) for s in watchlist_service.list_symbols(user_id) if s}
            except Exception:
                codes = set()
        from app.modules.market_data.services.cn_quote_snapshot import get_cn_quote_snapshot

        snapshot = get_cn_quote_snapshot()
        snapshot.ensure_fresh()
        payload = snapshot.query_page(
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_order=sort_order,
            board_filter=board_filter,
            codes=codes,
        )
        if scope in {"watchlist", "symbols"}:
            payload["scope"] = scope
        return ok_response(
            data=payload,
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
