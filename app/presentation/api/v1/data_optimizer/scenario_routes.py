"""Data optimizer scenario routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.presentation.api.common import ok_resource
from app.presentation.api.v1.data_optimizer._helpers import (
    parse_symbols_param,
    require_symbols,
    resolve_tdx_root,
    scenario_service,
)
from app.presentation.api.v1_context import ApiV1Context


def register_data_optimizer_scenario_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
) -> None:
    _ = ctx

    @blueprint.get("/data/scenarios")
    @login_required
    def data_scenarios():
        """List available data access scenarios."""
        from app.modules.strategy.services.strategy.scenario_optimizer_service import DataAccessScenario

        scenarios = [
            {"name": s.value, "description": desc}
            for s, desc in [
                (DataAccessScenario.MARKET_SCAN, "Full market scan with batch preload"),
                (DataAccessScenario.SINGLE_STOCK_ANALYSIS, "Single stock analysis with caching"),
                (DataAccessScenario.BACKTEST, "Backtest with preloaded data"),
                (DataAccessScenario.REALTIME_MONITOR, "Realtime monitoring"),
                (DataAccessScenario.HISTORICAL_RESEARCH, "Historical research"),
                (DataAccessScenario.WRITER_RESULT, "Write operation"),
            ]
        ]

        return ok_resource(
            resource={"scenarios": scenarios},
            resource_key="scenarios",
            enable_legacy_alias=False,
        )

    @blueprint.get("/data/scan-market")
    @login_required
    def data_scan_market():
        """Scan market - optimized for TDX file access."""
        symbols = parse_symbols_param(request.args.get("symbols", ""))
        require_symbols(symbols)

        tdx_root = resolve_tdx_root()
        service = scenario_service(tdx_root)
        results = service.scan_market(symbols)

        return ok_resource(
            resource={
                "symbols_processed": len(results),
                "data": {sym: len(data) for sym, data in results.items()},
            },
            resource_key="market_scan",
            enable_legacy_alias=False,
        )

    @blueprint.get("/data/backtest")
    @login_required
    def data_backtest():
        """Run backtest with TDX data."""
        symbols = parse_symbols_param(request.args.get("symbols", ""))
        require_symbols(symbols)

        start = request.args.get("start", "2020-01-01")
        end = request.args.get("end", "2024-12-31")

        tdx_root = resolve_tdx_root()
        service = scenario_service(tdx_root)
        results = service.run_backtest(symbols, start, end)

        total_bars = sum(len(data) for data in results.values())

        return ok_resource(
            resource={
                "symbols_loaded": len(results),
                "total_bars": total_bars,
                "date_range": f"{start} to {end}",
            },
            resource_key="backtest_data",
            enable_legacy_alias=False,
        )
