"""One-click deploy and Jarvis execute routes."""

from __future__ import annotations

import logging

from flask import Blueprint, request
from flask_login import current_user

from app.application.errors import ExternalServiceError, ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.v1.one_click.runtime import OneClickRuntime
from app.presentation.api.v1_context import ApiV1Context

logger = logging.getLogger(__name__)


def register_one_click_action_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: OneClickRuntime,
) -> None:
    _ = ctx

    @blueprint.route("/deploy", methods=["POST"])
    def deploy_strategy():
        """One-click deploy a shared WisdomMesh strategy."""
        data = request.get_json(silent=True) or {}
        strategy_id = str(data.get("strategy_id") or "").strip()
        symbol = str(data.get("symbol") or "").strip()

        if not strategy_id or not symbol:
            raise ValidationError("strategy_id_and_symbol_required")

        svc = runtime.require_service()
        try:
            user_id = str(getattr(current_user, "id", "anonymous"))
            result = svc.deploy_shared_strategy(
                user_id=user_id,
                strategy_id=strategy_id,
                symbol=symbol,
                market=str(data.get("market", "CN")),
                account_equity=float(data.get("account_equity", 100000)),
            )
            return ok_response(data=result)
        except ValidationError:
            raise
        except Exception as exc:
            logger.exception("one_click.deploy failed")
            raise ExternalServiceError(
                "deploy_failed",
                details={"reason": str(exc)},
            ) from exc

    @blueprint.route("/execute", methods=["POST"])
    def jarvis_execute():
        """Jarvis one-click execution."""
        data = request.get_json(silent=True) or {}
        strategy_id = str(data.get("strategy_id") or "").strip()
        symbol = str(data.get("symbol") or "").strip()
        side = str(data.get("side") or "").strip()
        quantity = int(data.get("quantity", 0))
        price = float(data.get("price", 0))

        if not strategy_id or not symbol:
            raise ValidationError("strategy_id_and_symbol_required")

        svc = runtime.require_service()
        try:
            user_id = str(getattr(current_user, "id", "anonymous"))
            result = svc.jarvis_execute(
                user_id=user_id,
                strategy_id=strategy_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
            )
            return ok_response(data=result)
        except ValidationError:
            raise
        except Exception as exc:
            logger.exception("one_click.execute failed")
            raise ExternalServiceError(
                "execute_failed",
                details={"reason": str(exc)},
            ) from exc
