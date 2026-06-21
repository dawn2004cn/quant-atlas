from __future__ import annotations
"""API v1: Strategy optimization routes."""


from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import ValidationError
from ...core.registry import register_routes
from .common import ok_resource, ok_response
from .v1_context import ApiV1Context
from .request_parsers import parse_int_param
from .decorators import service_fallback


@register_routes(name="strategy_optimization", context="strategy", description="Strategy optimization routes")
def register_strategy_optimization_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    @blueprint.post("/strategy/walk-forward")
    @login_required
    @service_fallback("strategy_optimization_service")
    def strategy_walk_forward():
        """Run walk-forward parameter optimization."""
        body = request.get_json(silent=True) or {}

        symbol = body.get("symbol", "").strip().upper()
        if not symbol:
            raise ValidationError("symbol_required")

        param_space = body.get("param_space", {})
        if not param_space:
            raise ValidationError("param_space_required")

        start_date = body.get("start_date", "")
        end_date = body.get("end_date", "")
        if not start_date or not end_date:
            raise ValidationError("start_date_and_end_date_required")

        objective = str(body.get("objective", "sharpe_ratio")).strip().lower()
        train_window_days = parse_int_param(body.get("train_window_days"), name="train_window_days", default=252)
        test_window_days = parse_int_param(body.get("test_window_days"), name="test_window_days", default=63)
        n_windows = parse_int_param(body.get("n_windows"), name="n_windows", default=5)

        result = service.run_walk_forward(
            symbol=symbol,
            param_space=param_space,
            start_date=start_date,
            end_date=end_date,
            objective=objective,
            train_window_days=train_window_days,
            test_window_days=test_window_days,
            n_windows=n_windows,
        )

        return ok_resource(
            resource=result.model_dump(),
            resource_key="walk_forward",
            enable_legacy_alias=False,
        )