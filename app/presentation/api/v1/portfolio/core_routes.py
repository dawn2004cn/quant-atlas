"""Portfolio optimization and analytics routes."""

from __future__ import annotations

import logging

from flask import Blueprint, request
from flask_login import login_required

from app.application.dto import OptimizationRequestDTO
from app.application.errors import ValidationError
from app.presentation.api.common import ok_resource, ok_response
from app.presentation.api.request_parsers import parse_float_param, parse_int_param
from app.presentation.api.route_deps import PortfolioRouteDeps
from app.presentation.api.v1.portfolio._helpers import parse_symbols_param, require_symbols
from app.presentation.api.v1_context import ApiV1Context

logger = logging.getLogger(__name__)


def register_portfolio_core_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    route_deps: PortfolioRouteDeps,
) -> None:
    _ = ctx
    portfolio_service = route_deps.portfolio_service

    @blueprint.get("/portfolio/snapshot")
    @login_required
    def portfolio_snapshot():
        """Get current portfolio snapshot."""
        symbols = parse_symbols_param(request.args.get("symbols", ""))
        require_symbols(symbols)

        cash = parse_float_param(request.args.get("cash"), name="cash", default=0.0)
        holdings = {}
        for sym in symbols:
            shares = parse_int_param(request.args.get(f"shares_{sym}"), name=f"shares_{sym}", default=100)
            if shares and shares > 0:
                holdings[sym] = shares

        if not holdings:
            holdings = {s: 100 for s in symbols}

        snapshot = portfolio_service.get_portfolio_snapshot(symbols, holdings, cash)
        return ok_resource(
            resource=snapshot.model_dump(),
            resource_key="portfolio",
            enable_legacy_alias=False,
        )

    @blueprint.post("/portfolio/optimize")
    @login_required
    def portfolio_optimize():
        """Run portfolio optimization."""
        body = request.get_json(silent=True) or {}
        symbols = body.get("symbols") or request.args.getlist("symbols")
        if not symbols:
            raise ValidationError("symbols_required")

        method = str(body.get("method", "markowitz")).strip().lower()
        target_return = parse_float_param(body.get("target_return"), name="target_return", default=None)
        if target_return is not None:
            target_return = target_return / 100.0

        risk_aversion = parse_float_param(body.get("risk_aversion"), name="risk_aversion", default=1.0)
        analyst_views = body.get("analyst_views")

        request_dto = OptimizationRequestDTO(
            symbols=symbols if isinstance(symbols, list) else [s.strip() for s in str(symbols).split(",") if s.strip()],
            method=method,
            target_return=target_return,
            risk_aversion=risk_aversion,
            analyst_views=analyst_views,
        )

        result = portfolio_service.optimize_portfolio(request_dto)
        return ok_resource(
            resource=result.model_dump(),
            resource_key="optimization",
            enable_legacy_alias=False,
        )

    @blueprint.get("/portfolio/rebalance")
    @login_required
    def portfolio_rebalance():
        """Check rebalance alerts for portfolio."""
        symbols = parse_symbols_param(request.args.get("symbols", ""))
        require_symbols(symbols)

        holdings = {}
        for sym in symbols:
            shares = parse_int_param(request.args.get(f"shares_{sym}"), name=f"shares_{sym}", default=100)
            holdings[sym] = shares or 100

        cash = parse_float_param(request.args.get("cash"), name="cash", default=0.0)
        threshold = parse_float_param(request.args.get("threshold"), name="threshold", default=5.0) / 100.0

        target_weights_str = request.args.get("target_weights", "")
        target_weights = {}
        if target_weights_str:
            for item in target_weights_str.split(","):
                parts = item.split(":")
                if len(parts) == 2:
                    sym = parts[0].strip()
                    try:
                        target_weights[sym] = float(parts[1].strip()) / 100.0
                    except ValueError as exc:
                        logger.warning("portfolio_rebalance target_weights: %s", exc)

        snapshot = portfolio_service.get_portfolio_snapshot(symbols, holdings, cash)

        if target_weights:
            alerts = portfolio_service.check_rebalance_alerts(snapshot, target_weights, threshold)
        else:
            opt_result = portfolio_service.optimize_portfolio(
                OptimizationRequestDTO(symbols=symbols, method="markowitz")
            )
            alerts = portfolio_service.check_rebalance_alerts(snapshot, opt_result.optimal_weights, threshold)

        return ok_response(
            data={
                "rebalance": {
                    "snapshot": snapshot.model_dump() if hasattr(snapshot, "model_dump") else snapshot,
                    "actions": [a.model_dump() for a in alerts],
                    "holdings": snapshot.positions if hasattr(snapshot, "positions") else [],
                },
            },
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )

    @blueprint.get("/portfolio/attribution")
    @login_required
    def portfolio_attribution():
        """Analyze portfolio attribution (Beta, Alpha, Style)."""
        portfolio_return = parse_float_param(request.args.get("portfolio_return"), name="portfolio_return", default=0.0) / 100.0
        benchmark_return = parse_float_param(request.args.get("benchmark_return"), name="benchmark_return", default=0.0) / 100.0
        alpha = parse_float_param(request.args.get("alpha"), name="alpha", default=0.0) / 100.0

        factor_exposures = {}
        factor_returns = {}
        for key, val in request.args.items():
            if key.startswith("exposure_"):
                factor = key[10:]
                try:
                    factor_exposures[factor] = float(val) / 100.0
                except ValueError as exc:
                    logger.warning("portfolio_attribution exposure: %s", exc)
            if key.startswith("factor_"):
                factor = key[7:]
                try:
                    factor_returns[factor] = float(val) / 100.0
                except ValueError as exc:
                    logger.warning("portfolio_attribution factor: %s", exc)

        result = portfolio_service.analyze_attribution(
            portfolio_return=portfolio_return,
            benchmark_return=benchmark_return,
            factor_exposures=factor_exposures,
            factor_returns=factor_returns,
            alpha=alpha,
        )
        return ok_resource(
            resource=result.model_dump(),
            resource_key="attribution",
            enable_legacy_alias=False,
        )

    @blueprint.get("/portfolio/risk-budget")
    @login_required
    def portfolio_risk_budget():
        """Compute risk budget per asset."""
        symbols = parse_symbols_param(request.args.get("symbols", ""))
        require_symbols(symbols)

        holdings = {}
        for sym in symbols:
            shares = parse_int_param(request.args.get(f"shares_{sym}"), name=f"shares_{sym}", default=100)
            holdings[sym] = shares or 100

        risks = portfolio_service.compute_risk_budget(symbols, holdings)
        return ok_response(
            data={"risk_budget": risks},
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )
