"""Strategy synthesis evidence card route."""

from __future__ import annotations

import json
import logging

from flask import Blueprint, request

from app.application.errors import ExternalServiceError, ValidationError
from app.domain.strategies.strategy_synthesizer_models import StrategySpec
from app.presentation.api.common import ok_response
from app.presentation.api.v1.strategy_synthesis.runtime import StrategySynthesisRuntime
from app.presentation.api.v1_context import ApiV1Context

logger = logging.getLogger(__name__)


def register_strategy_synthesis_evidence_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: StrategySynthesisRuntime,
) -> None:
    _ = ctx

    @blueprint.route("/evidence-card", methods=["GET"])
    def evidence_card():
        """Generate an evidence card for a strategy + symbol."""
        strategy_id = (request.args.get("strategy_id") or "").strip()
        symbol = (request.args.get("symbol") or "").strip()
        spec_json = (request.args.get("spec") or "").strip()

        if not spec_json and not strategy_id:
            raise ValidationError("spec_or_strategy_id_required")

        svc = runtime.synthesizer
        if svc is None:
            return runtime.unavailable_response()

        try:
            if spec_json:
                spec_dict = json.loads(spec_json)
            else:
                spec_dict = {}

            spec = StrategySpec.from_dict(spec_dict)
            card = svc.synthesize_evidence_card(spec, symbol=symbol)
            return ok_response(data=card)
        except ValidationError:
            raise
        except Exception as exc:
            logger.exception("strategy_synthesis.evidence_card failed")
            raise ExternalServiceError(
                "evidence_card_failed",
                details={"reason": str(exc)},
            ) from exc
