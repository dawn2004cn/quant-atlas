"""Risk companion emotion detection route."""

from __future__ import annotations

import logging

from flask import Blueprint, request

from app.application.errors import ExternalServiceError, ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.v1.risk_companion.runtime import RiskCompanionRuntime
from app.presentation.api.v1_context import ApiV1Context

logger = logging.getLogger(__name__)


def register_risk_companion_detect_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: RiskCompanionRuntime,
) -> None:
    _ = ctx

    @blueprint.route("/detect", methods=["POST"])
    def detect_emotion():
        """Detect emotion patterns from recent trade data."""
        data = request.get_json(silent=True) or {}
        user_id = str(data.get("user_id") or "").strip()
        trades = data.get("trades", [])

        if not user_id:
            raise ValidationError("user_id_required")

        svc = runtime.require_service()
        try:
            signal = svc.detect_emotion_pattern(user_id, trades)
            message = svc.generate_companion_message(signal)
            return ok_response(data={
                "signal": signal.to_dict(),
                "message": message.to_dict(),
            })
        except ValidationError:
            raise
        except Exception as exc:
            logger.exception("risk_companion.detect failed")
            raise ExternalServiceError(
                "detect_failed",
                details={"reason": str(exc)},
            ) from exc
