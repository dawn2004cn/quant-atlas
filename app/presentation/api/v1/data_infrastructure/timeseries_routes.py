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
        end_d = date.today()
        start_d = end_d - timedelta(days=days)
        provider = get_multi_source_history_provider()
        bars = provider.get_history(symbol, market, start_d, end_d)
        return ok_response(
            data={
                "symbol": symbol,
                "market": market.value,
                "bars": bars[-min(len(bars), 120) :],
                "count": len(bars),
                "source": provider.last_source,
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
