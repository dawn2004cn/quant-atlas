"""Wisdom mesh strategy sharing routes."""

from __future__ import annotations

import logging

from flask import Blueprint, request
from flask_login import current_user

from app.application.errors import ExternalServiceError, ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.v1.wisdom_mesh.runtime import WisdomMeshRuntime
from app.presentation.api.v1_context import ApiV1Context

logger = logging.getLogger(__name__)


def register_wisdom_mesh_strategy_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: WisdomMeshRuntime,
) -> None:
    _ = ctx

    @blueprint.route("/strategies", methods=["GET"])
    def list_strategies():
        """Browse shared strategies."""
        filter_by = request.args.get("filter_by", "top")
        limit = int(request.args.get("limit", 20))
        svc = runtime.require_service()
        try:
            strategies = svc.list_shared_strategies(limit=limit, filter_by=filter_by)
            return ok_response(data={"strategies": strategies, "total": len(strategies)})
        except Exception as exc:
            logger.exception("wisdom_mesh.list failed")
            raise ExternalServiceError(
                "list_failed",
                details={"reason": str(exc)},
            ) from exc

    @blueprint.route("/strategies", methods=["POST"])
    def upload_strategy():
        """Upload a de-identified strategy to the Wisdom Mesh."""
        data = request.get_json(silent=True) or {}
        strategy_spec = data.get("strategy_spec")
        performance_summary = data.get("performance_summary", {})

        if not strategy_spec:
            raise ValidationError("strategy_spec_required")

        svc = runtime.require_service()
        try:
            user_id = str(getattr(current_user, "id", "anonymous"))
            strategy = svc.upload_deidentified_strategy(
                user_id=user_id,
                strategy_spec=strategy_spec,
                performance_summary=performance_summary,
            )
            return ok_response(data=strategy.to_dict())
        except ValidationError:
            raise
        except Exception as exc:
            logger.exception("wisdom_mesh.upload failed")
            raise ExternalServiceError(
                "upload_failed",
                details={"reason": str(exc)},
            ) from exc

    @blueprint.route("/strategies/<strategy_id>", methods=["GET"])
    def get_strategy(strategy_id):
        """Get a single shared strategy by ID."""
        svc = runtime.require_service()
        try:
            result = svc.get_shared_strategy(strategy_id)
            if result is None:
                raise ValidationError("strategy_not_found")
            return ok_response(data=result)
        except ValidationError:
            raise
        except Exception as exc:
            logger.exception("wisdom_mesh.get failed")
            raise ExternalServiceError(
                "get_failed",
                details={"reason": str(exc)},
            ) from exc

    @blueprint.route("/strategies/<strategy_id>/vote", methods=["POST"])
    def vote_factor(strategy_id):
        """Vote on a factor tweak for a shared strategy."""
        data = request.get_json(silent=True) or {}
        factor_name = str(data.get("factor_name") or "").strip()
        proposed_weight = float(data.get("proposed_weight", 0))
        rationale = str(data.get("rationale") or "").strip()

        if not factor_name:
            raise ValidationError("factor_name_required")

        svc = runtime.require_service()
        try:
            voter_id = str(getattr(current_user, "id", "anonymous"))
            contribution = svc.vote_on_factor(
                voter_id=voter_id,
                strategy_id=strategy_id,
                factor_name=factor_name,
                proposed_weight=proposed_weight,
                rationale=rationale,
            )
            return ok_response(data=contribution.to_dict())
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        except Exception as exc:
            logger.exception("wisdom_mesh.vote failed")
            raise ExternalServiceError(
                "vote_failed",
                details={"reason": str(exc)},
            ) from exc
