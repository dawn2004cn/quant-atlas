from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.bootstrap_components.service_wiring import _get_registry
from app.core.logger import get_logger
from app.core.registry import ServiceRegistry, register_routes
from app.modules.strategy.services.strategy.strategy_wizard_service import StrategyWizardService
from app.presentation.api.error_codes import ErrorCode, error_payload
from app.presentation.api.responses import success_response

logger = get_logger(__name__)


def _validation_error(message: str):
    payload = error_payload(ErrorCode.VALIDATION_ERROR, message)
    return jsonify(payload), ErrorCode.VALIDATION_ERROR.http_status


def _not_found(message: str):
    payload = error_payload(ErrorCode.NOT_FOUND, message)
    return jsonify(payload), ErrorCode.NOT_FOUND.http_status


def _internal_error(exc: Exception):
    payload = error_payload(ErrorCode.INTERNAL_ERROR, str(exc))
    return jsonify(payload), ErrorCode.INTERNAL_ERROR.http_status


@register_routes(name="strategy_wizard", context="strategy", description="Strategy wizard templates and deploy")
def register_strategy_wizard_routes(blueprint, ctx):
    """Register the strategy wizard routes under /strategy/wizard."""
    _ = ctx
    registry: ServiceRegistry = _get_registry()
    wizard_bp = Blueprint("strategy_wizard", __name__, url_prefix="/strategy/wizard")

    @wizard_bp.route("/templates", methods=["GET"])
    def list_templates():
        wizard_service: StrategyWizardService = registry.get("strategy_wizard_service")
        try:
            return success_response(data=wizard_service.get_wizard_start_data())
        except Exception as exc:
            logger.exception("Failed to list templates")
            return _internal_error(exc)

    @wizard_bp.route("/template/<template_id>", methods=["GET"])
    def get_template(template_id: str):
        wizard_service: StrategyWizardService = registry.get("strategy_wizard_service")
        try:
            return success_response(data=wizard_service.get_template_config(template_id))
        except ValueError as exc:
            return _not_found(str(exc))
        except Exception as exc:
            logger.exception("Failed to get template %s", template_id)
            return _internal_error(exc)

    @wizard_bp.route("/preview", methods=["POST"])
    async def preview_strategy():
        wizard_service: StrategyWizardService = registry.get("strategy_wizard_service")
        data = request.json or {}
        template_id = data.get("template_id")
        user_params = data.get("params", {})
        if not template_id:
            return _validation_error("template_id is required")
        try:
            result = await wizard_service.preview_strategy(template_id, user_params)
            return success_response(data=result)
        except ValueError as exc:
            return _validation_error(str(exc))
        except Exception as exc:
            logger.exception("Strategy preview failed")
            return _internal_error(exc)

    @wizard_bp.route("/create", methods=["POST"])
    def create_strategy():
        wizard_service: StrategyWizardService = registry.get("strategy_wizard_service")
        data = request.json or {}
        template_id = data.get("template_id")
        user_params = data.get("params", {})
        risk_settings = data.get("risk_settings", {})
        if not template_id:
            return _validation_error("template_id is required")
        try:
            result = wizard_service.create_from_wizard(template_id, user_params, risk_settings)
            if result.get("status") == "created":
                return success_response(data=result, code=201)
            return _validation_error(str(result.get("error", "create_failed")))
        except Exception as exc:
            logger.exception("Strategy creation failed")
            return _internal_error(exc)

    blueprint.register_blueprint(wizard_bp)
