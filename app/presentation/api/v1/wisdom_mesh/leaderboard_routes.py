"""Wisdom mesh leaderboard route."""

from __future__ import annotations

import logging

from flask import Blueprint, request

from app.application.errors import ExternalServiceError
from app.presentation.api.common import ok_response
from app.presentation.api.v1.wisdom_mesh.runtime import WisdomMeshRuntime
from app.presentation.api.v1_context import ApiV1Context

logger = logging.getLogger(__name__)


def register_wisdom_mesh_leaderboard_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: WisdomMeshRuntime,
) -> None:
    _ = ctx

    @blueprint.route("/leaderboard", methods=["GET"])
    def leaderboard():
        """User participation leaderboard."""
        period = request.args.get("period", "weekly")
        svc = runtime.require_service()
        try:
            lb = svc.get_leaderboard(period=period)
            return ok_response(data={"leaderboard": lb})
        except Exception as exc:
            logger.exception("wisdom_mesh.leaderboard failed")
            raise ExternalServiceError(
                "leaderboard_failed",
                details={"reason": str(exc)},
            ) from exc
