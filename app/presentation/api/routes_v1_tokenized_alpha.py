"""Tokenized Alpha API — Phase 16 routes for factor tokenization & hero board."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import login_required

from app.core.logger import get_logger
from app.core.registry import register_routes
from app.modules.system.services.alpha.tokenized_alpha_service import TokenizedAlphaService
from app.presentation.api.error_codes import ErrorCode, error_payload
from app.presentation.api.responses import success_response

logger = get_logger(__name__)


def _get_service() -> TokenizedAlphaService:
    return TokenizedAlphaService()


def _validation_error(message: str):
    payload = error_payload(ErrorCode.VALIDATION_ERROR, message)
    return jsonify(payload), ErrorCode.VALIDATION_ERROR.http_status


def _register_tokenized_alpha_routes(blueprint: Blueprint, ctx=None) -> None:
    _ = ctx
    alpha_bp = Blueprint("tokenized_alpha", __name__, url_prefix="/alpha/tokens")

    @alpha_bp.post("/mint")
    @login_required
    def mint_token():
        data = request.get_json(silent=True) or {}
        factor_id = data.get("factor_id", "")
        owner_id = data.get("user_id", 0)
        performance = data.get("performance", {})
        metadata = data.get("metadata", {})

        if not factor_id or not owner_id:
            return _validation_error("factor_id and user_id required")

        try:
            manifest = _get_service().tokenize_factor(factor_id, owner_id, performance, metadata)
        except Exception as exc:
            logger.warning("Token mint failed: %s", exc)
            return _validation_error(str(exc))

        return success_response(
            data={
                "token_id": manifest.token_id,
                "token_name": manifest.token_name,
                "token_symbol": manifest.token_symbol,
                "contract_address": manifest.contract_address,
                "visibility": manifest.visibility,
                "created_at": manifest.created_at,
            },
        )

    @alpha_bp.get("/<token_id>")
    @login_required
    def get_token(token_id):
        manifest = _get_service().get_manifest(token_id)
        if not manifest:
            payload = error_payload(ErrorCode.NOT_FOUND, "not_found")
            return jsonify(payload), ErrorCode.NOT_FOUND.http_status
        return success_response(
            data={
                "token_id": manifest.token_id,
                "factor_id": manifest.factor_id,
                "owner_id": manifest.owner_id,
                "token_name": manifest.token_name,
                "token_symbol": manifest.token_symbol,
                "description": manifest.description,
                "ic_history": manifest.ic_history[-5:],
                "live_performance": manifest.live_performance,
                "visibility": manifest.visibility,
                "contract_address": manifest.contract_address,
            },
        )

    @alpha_bp.get("/hero-board")
    @login_required
    def hero_board():
        board = _get_service().get_hero_board(limit=10)
        return success_response(data={"heroes": board})

    @alpha_bp.get("/reputation/<int:user_id>")
    @login_required
    def get_reputation(user_id):
        rec = _get_service()._get_reputation_record(user_id)
        if not rec:
            return success_response(
                data={
                    "user_id": user_id,
                    "reputation_score": 0.0,
                    "contribution_count": 0,
                    "live_days": 0,
                },
            )
        return success_response(
            data={
                "user_id": rec.user_id,
                "reputation_score": round(rec.reputation_score, 2),
                "contribution_count": rec.contribution_count,
                "live_days": rec.live_days,
                "last_live_at": rec.last_live_at,
            },
        )

    blueprint.register_blueprint(alpha_bp)


# Backward compat for smoke tests / legacy bootstrap imports
blueprint = Blueprint("tokenized_alpha", __name__, url_prefix="/alpha/tokens")


@register_routes(name="tokenized_alpha", context="system", description="Tokenized alpha factor marketplace")
def register_tokenized_alpha_routes(blueprint, ctx) -> None:
    _register_tokenized_alpha_routes(blueprint, ctx)
