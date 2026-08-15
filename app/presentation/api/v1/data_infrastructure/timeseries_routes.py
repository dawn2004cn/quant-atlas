from __future__ import annotations

from datetime import date, timedelta

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.domain.enums import MarketCode
from app.infrastructure.providers.history_adapters import get_multi_source_history_provider
from app.presentation.api.common import ok_response
from app.presentation.api.request_parsers import parse_int_param


def register_data_timeseries_routes(blueprint: Blueprint, *, legacy: bool) -> None:
    @blueprint.get("/data/timeseries-health")
    @login_required
    def data_timeseries_health():
        from app.infrastructure.timeseries.timeseries_factory import timeseries_health_probe

        return ok_response(
            data=timeseries_health_probe(),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/data/timeseries-sync-history")
    @login_required
    def data_timeseries_sync_history():
        from app.infrastructure.timeseries.sync_snapshot import get_timeseries_sync_history

        limit = parse_int_param(
            request.args.get("limit"),
            name="limit",
            default=20,
            min_value=1,
            max_value=100,
        )
        source = (request.args.get("source") or "").strip() or None
        runs = get_timeseries_sync_history(limit=limit, source=source)
        return ok_response(
            data={
                "runs": runs,
                "limit": limit,
                "source_filter": source,
                "count": len(runs),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/data/timeseries-bars")
    @login_required
    def data_timeseries_bars():
        symbol = request.args.get("symbol", "").strip().upper()
        if not symbol:
            raise ValidationError("symbol_required")
        market = MarketCode.CN
        days = parse_int_param(request.args.get("days"), name="days", default=60, min_value=5)
        from app.domain.shared.history_adjust import normalize_adjust, try_local_cn_history

        adjust = normalize_adjust(request.args.get("adjust"))
        end_d = date.today()
        start_d = end_d - timedelta(days=days)
        bars: list = []
        source = None
        adjust_meta: dict = {}
        local_bars, adjust_meta = try_local_cn_history(
            symbol, start_d.isoformat(), end_d.isoformat(), adjust
        )
        if local_bars:
            bars = local_bars
            source = adjust_meta.get("adjust_source")
        else:
            provider = get_multi_source_history_provider()
            bars = provider.get_history(symbol, market, start_d, end_d)
            source = provider.last_source
        return ok_response(
            data={
                "symbol": symbol,
                "market": market.value,
                "bars": bars[-min(len(bars), 120) :],
                "count": len(bars),
                "source": source,
                "adjust": adjust_meta.get("adjust", adjust),
                "adjust_applied": adjust_meta.get("adjust_applied", False),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/data/bars/batch")
    @login_required
    def data_bars_batch():
        """Batch OHLCV for multiple symbols (local-engine style bulk query)."""
        from app.domain.shared.history_adjust import normalize_adjust, try_local_cn_history

        body = request.get_json(silent=True) or {}
        symbols_raw = body.get("symbols") or []
        if isinstance(symbols_raw, str):
            symbols_raw = [s.strip() for s in symbols_raw.split(",")]
        symbols = [str(s).strip().upper() for s in symbols_raw if str(s).strip()]
        if not symbols:
            raise ValidationError("symbols_required")
        if len(symbols) > 50:
            raise ValidationError("symbols_limit_50")
        days = parse_int_param(body.get("days"), name="days", default=60, min_value=5, max_value=500)
        adjust = normalize_adjust(body.get("adjust"))
        market = MarketCode.CN
        end_d = date.today()
        start_d = end_d - timedelta(days=days)
        provider = get_multi_source_history_provider()
        items = []
        for symbol in symbols:
            bars, meta = try_local_cn_history(symbol, start_d.isoformat(), end_d.isoformat(), adjust)
            source = meta.get("adjust_source")
            if not bars:
                try:
                    bars = provider.get_history(symbol, market, start_d, end_d) or []
                    source = getattr(provider, "last_source", None)
                except Exception:  # noqa: BLE001
                    bars = []
            clipped = bars[-min(len(bars), 120) :] if bars else []
            items.append(
                {
                    "symbol": symbol,
                    "market": market.value,
                    "bars": clipped,
                    "count": len(clipped),
                    "source": source,
                    "adjust": meta.get("adjust", adjust),
                    "adjust_applied": bool(meta.get("adjust_applied")),
                }
            )
        return ok_response(
            data={"items": items, "count": len(items), "adjust": adjust, "days": days},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/data/sources")
    @login_required
    def data_sources_catalog():
        """List registered data sources (semantic registry introspection)."""
        from app.core.data_source_registry import get_data_source_registry

        registry = get_data_source_registry()
        type_filter = (request.args.get("type") or "").strip() or None
        scope = (request.args.get("scope") or "").strip() or None
        market = (request.args.get("market") or "").strip() or None
        sources = registry.find(type=type_filter, scope=scope, market=market)
        payload = [
            {
                "name": s.name,
                "type": s.type,
                "scope": s.scope,
                "market": s.market,
                "description": s.description,
                "priority": s.priority,
                "tags": list(s.tags),
            }
            for s in sources
        ]
        return ok_response(
            data={"items": payload, "stats": registry.stats(), "count": len(payload)},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
