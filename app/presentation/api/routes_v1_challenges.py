"""Challenge API Routes."""

from __future__ import annotations

from flask import Blueprint

from app.application.errors import ExternalServiceError
from app.core.registry import register_routes

from .common import ok_response

challenges_bp = Blueprint("challenges", __name__, url_prefix="/challenges")


@challenges_bp.route("/active", methods=["GET"])
def get_active_challenges():
    """Get active challenges."""
    try:
        from app.modules.execution.services.challenge_service import ChallengeManager

        manager = ChallengeManager()
        active = manager.get_active_challenges()

        return ok_response(
            data={
                "challenges": [
                    {
                        "challenge_id": c.challenge_id,
                        "name": c.config.name,
                        "description": c.config.description,
                        "status": c.status.value,
                        "start_date": c.config.start_date.isoformat(),
                        "end_date": c.config.end_date.isoformat(),
                        "participant_count": len(c.leaderboard.participants) if c.leaderboard else 0,
                    }
                    for c in active
                ],
            },
        )
    except Exception as exc:
        raise ExternalServiceError(
            "challenges_list_failed",
            details={"reason": str(exc)},
        ) from exc


@register_routes(name="challenge", context="trading", description="Trading challenge leaderboard")
def register_challenge_routes(blueprint, ctx=None) -> None:
    """Register challenge routes."""
    blueprint.register_blueprint(challenges_bp)
