from __future__ import annotations

"""API v1: strategy deploy snapshots and rollback."""

import logging

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.application.errors import ValidationError
from app.core.middleware.request_context import require_authenticated_user_id
from app.core.registry import register_routes
from app.modules.strategy.services.strategy.strategy_snapshot_service import StrategySnapshotService
from app.modules.system.services.ui.decision_snapshot_service import DecisionSnapshotService

from .common import ok_resource, ok_response
from .request_parsers import parse_int_param
from .v1_context import ApiV1Context

logger = logging.getLogger(__name__)


def _uid() -> int:
    return require_authenticated_user_id()


@register_routes(name="strategy_snapshot", context="strategy", description="Strategy deploy snapshots and rollback")
def register_strategy_snapshot_routes(blueprint: Blueprint, ctx: ApiV1Context | None = None) -> None:
    del ctx
    service = StrategySnapshotService()
    decision_snapshots = DecisionSnapshotService()

    def _actor() -> str:
        try:
            if current_user.is_authenticated:
                return str(getattr(current_user, "username", None) or _uid())
        except Exception:
            logger.debug("could not resolve username, defaulting to system")
        return "system"

    @blueprint.post("/strategy/snapshots")
    @login_required
    def strategy_snapshot_create():
        """Capture deploy snapshot: code revision, settings backup, benchmark metadata."""
        body = request.get_json(silent=True) or {}
        strategy_name = (body.get("strategy_name") or body.get("name") or "").strip()
        if not strategy_name:
            raise ValidationError("strategy_name_required")

        snapshot = service.capture_snapshot(
            strategy_name=strategy_name,
            label=str(body.get("label") or "").strip(),
            notes=str(body.get("notes") or "").strip(),
            strategy_config=body.get("strategy_config") if isinstance(body.get("strategy_config"), dict) else {},
            deployed_by=_actor(),
            mark_active=body.get("mark_active", True) is not False,
        )
        return ok_resource(
            resource=snapshot.model_dump(mode="json"),
            resource_key="snapshot",
        )

    @blueprint.get("/strategy/snapshots")
    @login_required
    def strategy_snapshot_list():
        """List deploy snapshots, optionally filtered by strategy name."""
        strategy_name = (request.args.get("strategy_name") or request.args.get("name") or "").strip() or None
        limit = parse_int_param(request.args.get("limit"), name="limit", default=50)
        rows = service.list_snapshots(strategy_name=strategy_name, limit=min(max(limit, 1), 200))
        return ok_response(
            data=[row.model_dump(mode="json") for row in rows],
            count=len(rows),
        )

    @blueprint.get("/strategy/snapshots/<snapshot_id>")
    @login_required
    def strategy_snapshot_get(snapshot_id: str):
        """Get one deploy snapshot by id."""
        snap = service.get_snapshot(snapshot_id)
        return ok_resource(resource=snap.model_dump(mode="json"), resource_key="snapshot")

    @blueprint.post("/strategy/snapshots/<snapshot_id>/rollback")
    @login_required
    def strategy_snapshot_rollback(snapshot_id: str):
        """Mark snapshot active; optionally restore config/settings.json."""
        body = request.get_json(silent=True) or {}
        apply_settings = body.get("apply_settings") is True or request.args.get("apply_settings") == "1"
        apply_code = body.get("apply_code") is True or request.args.get("apply_code") == "1"
        result = service.rollback(
            snapshot_id,
            rolled_back_by=_actor(),
            apply_settings=apply_settings,
            apply_code=apply_code,
        )
        return ok_resource(resource=result.model_dump(mode="json"), resource_key="rollback")

    @blueprint.post("/decision/snapshots")
    @login_required
    def decision_snapshot_create():
        """封存当前决策简报与行情快照，供团队复盘链接访问。"""
        body = request.get_json(silent=True) or {}
        brief = body.get("decision_brief")
        if not isinstance(brief, dict) or not brief:
            raise ValidationError("decision_brief_required")
        symbol = str(brief.get("symbol") or body.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol_required")
        market = str(brief.get("market") or body.get("market") or "CN").strip()
        snap = decision_snapshots.create_snapshot(
            symbol=symbol,
            market=market,
            decision_brief=brief,
            quote_snapshot=body.get("quote_snapshot") if isinstance(body.get("quote_snapshot"), dict) else None,
            sector_context=body.get("sector_context") if isinstance(body.get("sector_context"), dict) else None,
            label=str(body.get("label") or "").strip(),
            notes=str(body.get("notes") or "").strip(),
            created_by=_actor(),
        )
        return ok_resource(
            resource=snap.model_dump(mode="json"),
            resource_key="snapshot",
        )

    @blueprint.get("/decision/snapshots")
    @login_required
    def decision_snapshot_list():
        symbol = (request.args.get("symbol") or "").strip() or None
        limit = parse_int_param(request.args.get("limit"), name="limit", default=30)
        rows = decision_snapshots.list_snapshots(symbol=symbol, limit=min(max(limit, 1), 100))
        return ok_response(
            data=[r.model_dump(mode="json") for r in rows],
            count=len(rows),
        )

    @blueprint.get("/decision/snapshots/<snapshot_id>")
    @login_required
    def decision_snapshot_get(snapshot_id: str):
        snap = decision_snapshots.get_snapshot(snapshot_id)
        return ok_resource(resource=snap.model_dump(mode="json"), resource_key="snapshot")

    @blueprint.get("/decision/snapshots/public/<share_token>")
    def decision_snapshot_public_get(share_token: str):
        """只读分享：凭 share_token 获取封存简报（无需登录）。"""
        snap = decision_snapshots.get_snapshot_by_share_token(share_token)
        payload = snap.model_dump(mode="json")
        payload["read_only"] = True
        return ok_resource(resource=payload, resource_key="snapshot")
