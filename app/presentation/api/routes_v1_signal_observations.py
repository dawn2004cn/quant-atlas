from __future__ import annotations
"""API v1：信号模拟观察单。"""


from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import ValidationError
from ...core.middleware.request_context import require_authenticated_user_id
from ...core.registry import register_routes
from .common import ok_response, parse_market, ensure_service
from .request_parsers import parse_float_param
from .v1_context import ApiV1Context


def _uid() -> int:
    return require_authenticated_user_id()


def _optional_float_param(raw: object, *, name: str) -> float | None:
    if raw in (None, ""):
        return None
    return parse_float_param(raw, name=name, default=0.0)


@register_routes(name="signal_observation", context="portfolio_risk", description="信号模拟观察单")
def register_signal_observation_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register signal observation endpoints."""

    @blueprint.get("/signal-observations", strict_slashes=False)
    @login_required
    def list_signal_observations():
        svc = ensure_service(ctx, "signal_observation_service")
        payload = svc.list_observations(
            user_id=_uid(),
            status=(request.args.get("status") or "open"),
            refresh=True,
        )
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.get("/signal-observations/stats")
    @login_required
    def signal_observation_stats():
        svc = ensure_service(ctx, "signal_observation_service")
        return ok_response(
            data=svc.stats(user_id=_uid()),
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.post("/signal-observations")
    @login_required
    def add_signal_observation():
        svc = ensure_service(ctx, "signal_observation_service")
        body = request.get_json(silent=True) or {}
        symbol = str(body.get("symbol") or body.get("code") or "").strip()
        if not symbol:
            raise ValidationError("symbol_required")
        entry_price = _optional_float_param(body.get("entry_price"), name="entry_price")
        stop_loss = _optional_float_param(body.get("stop_loss"), name="stop_loss")
        target_price = _optional_float_param(body.get("target_price"), name="target_price")
        payload = svc.add_observation(
            symbol=symbol,
            market=parse_market(str(body.get("market") or "CN")),
            user_id=_uid(),
            name=str(body.get("name") or "").strip() or None,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            source=str(body.get("source") or "manual").strip() or "manual",
            reason=str(body.get("reason") or "").strip(),
            ai_summary=str(body.get("ai_summary") or "").strip(),
        )
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.delete("/signal-observations/<observation_id>")
    @login_required
    def delete_signal_observation(observation_id: str):
        svc = ensure_service(ctx, "signal_observation_service")
        payload = svc.close_observation(
            observation_id,
            user_id=_uid(),
            reason="manual_delete",
        )
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.post("/signal-observations/<observation_id>/close")
    @login_required
    def close_signal_observation(observation_id: str):
        svc = ensure_service(ctx, "signal_observation_service")
        body = request.get_json(silent=True) or {}
        payload = svc.close_observation(
            observation_id,
            user_id=_uid(),
            reason=str(body.get("reason") or "manual_close"),
        )
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.post("/signal-observations/<observation_id>/convert")
    @login_required
    def convert_observation_to_position(observation_id: str):
        svc = ensure_service(ctx, "signal_observation_service")
        body = request.get_json(silent=True) or {}
        payload = svc.convert_to_position(
            observation_id,
            user_id=_uid(),
            shares=body.get("shares"),
            cost_basis=body.get("cost_basis"),
        )
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.get("/signal-observations/positions")
    @login_required
    def list_positions():
        svc = ensure_service(ctx, "signal_observation_service")
        payload = svc.list_positions(user_id=_uid())
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.post("/signal-observations/<observation_id>/notes")
    @login_required
    def update_observation_notes(observation_id: str):
        svc = ensure_service(ctx, "signal_observation_service")
        body = request.get_json(silent=True) or {}
        notes = str(body.get("notes") or "").strip()
        if hasattr(svc, 'update_notes'):
            svc.update_notes(observation_id, _uid(), notes)
        return ok_response(
            data={"success": True},
            legacy_alias_key=None,
            enable_legacy_alias=ctx.enable_legacy_response_fields,
        )

    @blueprint.post("/signal-observations/batch")
    @login_required
    def batch_signal_observations():
        """Batch operate observation cards: complete / defer / ignore."""
        svc = ensure_service(ctx, "signal_observation_service")
        body = request.get_json(silent=True) or {}
        action = str(body.get("action") or "").strip()
        ids = body.get("ids") or []
        if not isinstance(ids, list) or not ids:
            raise ValidationError("ids_required")
        if action not in ("complete", "defer", "ignore"):
            raise ValidationError("action_must_be_complete_defer_or_ignore")
        user_id = _uid()
        results = []
        for oid in ids:
            oid = str(oid).strip()
            if not oid:
                continue
            try:
                if action == "complete":
                    svc.close_observation(oid, user_id=user_id, reason="batch_complete")
                elif action == "defer":
                    svc.update_notes(oid, user_id, "deferred")
                else:
                    svc.close_observation(oid, user_id=user_id, reason="batch_ignore")
                results.append({"id": oid, "ok": True})
            except Exception as exc:
                results.append({"id": oid, "ok": False, "error": str(exc)[:120]})
        return ok_response(data={"action": action, "results": results}, legacy_alias_key=None, enable_legacy_alias=ctx.enable_legacy_response_fields)

