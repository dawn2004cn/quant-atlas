"""Attribution what-if simulation route."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ExternalServiceError, ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.v1.attribution._helpers import DEFAULT_POSITIONS
from app.presentation.api.v1.attribution.runtime import AttributionRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_attribution_whatif_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context | None,
    *,
    runtime: AttributionRuntime,
) -> None:
    _ = ctx, runtime

    @blueprint.route("/whatif", methods=["POST"])
    @login_required
    def simulate_whatif():
        """What-if factor adjustment simulation."""
        data = request.get_json(silent=True) or {}
        adjustments = data.get("adjustments", {})

        try:
            from app.modules.strategy.services.analytics.attribution_service import WhatIfAnalyzer

            base_positions = data.get("positions") or DEFAULT_POSITIONS[:3]
            analyzer = WhatIfAnalyzer(base_positions)
            result = analyzer.simulate(adjustments)
            return ok_response(data=result)
        except (ValidationError, ExternalServiceError):
            raise
        except Exception as exc:
            raise ExternalServiceError(
                "attribution_whatif_failed",
                details={"reason": str(exc)},
            ) from exc
