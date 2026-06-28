from __future__ import annotations

from flask import Blueprint, jsonify

from app.application.errors import NotFoundError
from app.core.logger import get_logger
from app.core.registry import register_routes
from app.presentation.api.error_codes import ErrorCode, error_payload
from app.presentation.api.responses import success_response

logger = get_logger(__name__)


def _register_experiment_routes(blueprint: Blueprint, ctx=None) -> None:
    """Register experiment routes directly onto the blueprint."""
    _ = ctx
    exp_bp = Blueprint("experiments", __name__, url_prefix="/experiments")

    @exp_bp.route("", methods=["GET"])
    def list_experiments():
        """List all experiments."""
        try:
            from app.config import get_settings
            from app.infrastructure.repositories.deps import create_experiment_repository

            repo = create_experiment_repository(get_settings())
            experiments = repo.list_all()[:50]
            return success_response(
                data={"experiments": [e.to_api_summary() for e in experiments]},
            )
        except Exception as exc:
            logger.exception("list_experiments failed")
            payload = error_payload(ErrorCode.INTERNAL_ERROR, str(exc))
            return jsonify(payload), ErrorCode.INTERNAL_ERROR.http_status

    @exp_bp.route("/<exp_id>", methods=["GET"])
    def get_experiment(exp_id: str):
        """Get experiment details."""
        from app.config import get_settings
        from app.infrastructure.repositories.deps import create_experiment_repository

        repo = create_experiment_repository(get_settings())
        exp = repo.get(exp_id)
        if not exp:
            raise NotFoundError("experiment_not_found", details={"experiment_id": exp_id})
        return success_response(data=exp.to_api_detail())

    blueprint.register_blueprint(exp_bp)


@register_routes(name="experiments", context="system", description="Experiment management")
def register_experiments_routes(blueprint: Blueprint, ctx=None) -> None:
    _register_experiment_routes(blueprint, ctx)
