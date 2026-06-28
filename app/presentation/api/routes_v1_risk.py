from __future__ import annotations

"""API v1: Risk management routes."""


from flask import Blueprint, request
from flask_login import login_required

from app.domain.dto.risk_request_dto import (
    RiskCheckBatchRequest,
    RiskCheckOrderRequest,
    RiskKellyRequest,
    RiskVolatilityTargetRequest,
)

from ...application.errors import ValidationError
from ...core.registry import register_routes
from .common import ok_resource
from .dto_validation import validate_request
from .route_deps import RiskRouteDeps, build_risk_route_deps
from .v1_context import ApiV1Context


@register_routes(name="risk", context="portfolio_risk", description="Risk management routes")
def register_risk_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context | None = None,
    *,
    deps: RiskRouteDeps | None = None,
) -> None:
    route_deps = deps or build_risk_route_deps(ctx)
    risk_service = route_deps.risk_service
    legacy = route_deps.enable_legacy_response_fields

    @blueprint.post("/risk/check-order")
    @login_required
    @validate_request(RiskCheckOrderRequest)
    def risk_check_order(req: RiskCheckOrderRequest):
        """Pre-flight risk check for a single order."""
        result = risk_service.check_order(
            symbol=req.symbol.strip().upper(),
            side=req.side.strip().lower(),
            quantity=req.quantity,
            price=req.price,
            account_id=req.account_id,
            total_equity=req.total_equity,
        )

        return ok_resource(
            resource=result.model_dump() if hasattr(result, "model_dump") else result,
            resource_key="risk_check",
            enable_legacy_alias=False,
        )

    @blueprint.post("/risk/check-orders-batch")
    @login_required
    @validate_request(RiskCheckBatchRequest)
    def risk_check_orders_batch(req: RiskCheckBatchRequest):
        """Batch pre-flight risk checks."""
        if not req.orders:
            raise ValidationError("orders_required")

        result = risk_service.check_orders_batch(req.orders)

        return ok_resource(
            resource=result.model_dump() if hasattr(result, "model_dump") else result,
            resource_key="risk_batch",
            enable_legacy_alias=False,
        )

    @blueprint.post("/risk/position/volatility-target")
    @login_required
    @validate_request(RiskVolatilityTargetRequest)
    def risk_volatility_target(req: RiskVolatilityTargetRequest):
        """Compute volatility-target position size."""
        position_size = risk_service.compute_volatility_target_position(
            symbol=req.symbol.strip().upper(),
            target_vol=req.target_vol,
            lookback=req.lookback,
            total_equity=req.total_equity,
        )

        return ok_resource(
            resource={"symbol": req.symbol.strip().upper(), "position_size": position_size},
            resource_key="vol_target",
            enable_legacy_alias=False,
        )

    @blueprint.post("/risk/position/kelly")
    @login_required
    @validate_request(RiskKellyRequest)
    def risk_kelly_position(req: RiskKellyRequest):
        """Compute Kelly criterion position size."""
        kelly = risk_service.compute_kelly_position(
            win_rate=req.win_rate,
            avg_win=req.avg_win,
            avg_loss=req.avg_loss,
            total_equity=req.total_equity,
            fraction=req.fraction,
        )

        return ok_resource(
            resource={
                "kelly_fraction": kelly,
                "recommended_position": kelly * req.total_equity,
            },
            resource_key="kelly",
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/risk/entangled")
    @login_required
    def risk_entangled():
        """Analyze semantic entanglement between strategy positions."""
        body = request.get_json(silent=True) or {}
        positions = body.get("positions") if isinstance(body.get("positions"), list) else []
        total_value = float(body.get("total_value") or 0.0)
        svc = getattr(ctx, "risk_application_service", None)
        if svc is None:
            from app.modules.portfolio_risk.services.risk_application_service import RiskApplicationService

            svc = RiskApplicationService()
        return ok_resource(
            resource=svc.analyze_entangled_risk(positions, total_value),
            resource_key="entangled_risk",
            enable_legacy_alias=False,
        )
