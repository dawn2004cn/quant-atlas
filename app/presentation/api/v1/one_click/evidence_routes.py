"""One-click evidence card route."""

from __future__ import annotations

import logging

from flask import Blueprint, request

from app.application.errors import ExternalServiceError, ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.v1.one_click.runtime import OneClickRuntime
from app.presentation.api.v1_context import ApiV1Context

logger = logging.getLogger(__name__)


def register_one_click_evidence_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: OneClickRuntime,
) -> None:
    _ = ctx

    @blueprint.route("/evidence-card", methods=["GET"])
    def evidence_card():
        """Evidence card for a shared strategy."""
        strategy_id = (request.args.get("strategy_id") or "").strip()
        symbol = (request.args.get("symbol") or "").strip()

        if not strategy_id:
            raise ValidationError("strategy_id_required")

        svc = runtime.require_service()
        try:
            result = svc.generate_evidence_card(strategy_id, symbol)
            return ok_response(data=result)
        except Exception as exc:
            logger.exception("one_click.evidence_card failed")
            raise ExternalServiceError(
                "evidence_card_failed",
                details={"reason": str(exc)},
            ) from exc
