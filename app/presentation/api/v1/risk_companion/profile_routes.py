"""Risk companion DNA and XP routes."""

from __future__ import annotations

import logging

from flask import Blueprint, request
from flask_login import current_user

from app.application.errors import ExternalServiceError, ValidationError
from app.domain.risk.risk_companion_models import XpEventType
from app.presentation.api.common import ok_response
from app.presentation.api.v1.risk_companion.runtime import RiskCompanionRuntime
from app.presentation.api.v1_context import ApiV1Context

logger = logging.getLogger(__name__)


def register_risk_companion_profile_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: RiskCompanionRuntime,
) -> None:
    _ = ctx

    @blueprint.route("/dna", methods=["GET"])
    def get_trading_dna():
        """Get user's Trading DNA profile for spiral visualization."""
        user_id = (request.args.get("user_id") or "").strip()

        svc = runtime.require_service()
        try:
            if not user_id:
                user_id = str(getattr(current_user, "id", "anonymous"))

            profile = svc.get_trading_dna(user_id)
            return ok_response(data=profile.to_dict())
        except Exception as exc:
            logger.exception("risk_companion.dna failed")
            raise ExternalServiceError(
                "dna_failed",
                details={"reason": str(exc)},
            ) from exc

    @blueprint.route("/xp", methods=["POST"])
    def award_xp():
        """Award XP for prudent trading behavior."""
        data = request.get_json(silent=True) or {}
        user_id = str(data.get("user_id") or "").strip()
        event_type = str(data.get("event_type") or "").strip()

        if not user_id or not event_type:
            raise ValidationError("user_id_and_event_type_required")

        svc = runtime.require_service()
        try:
            xp_event = XpEventType(event_type)
            result = svc.award_xp(user_id, xp_event, context=data.get("context", ""))
            return ok_response(data=result)
        except ValueError as exc:
            raise ValidationError(f"invalid_event_type: {event_type}") from exc
        except Exception as exc:
            logger.exception("risk_companion.xp failed")
            raise ExternalServiceError(
                "xp_failed",
                details={"reason": str(exc)},
            ) from exc
