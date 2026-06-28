"""Swarm adaptive topology routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.presentation.api.common import ok_response
from app.presentation.api.v1.swarm_topology._helpers import adaptive_service, unavailable_response
from app.presentation.api.v1.swarm_topology.runtime import SwarmTopologyRuntime
from app.presentation.api.v1_context import ApiV1Context

from ...decorators import require_role


def register_swarm_topology_adaptive_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: SwarmTopologyRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.get("/swarm/topology/adaptive/state")
    @login_required
    def swarm_topology_adaptive_state():
        svc = adaptive_service(runtime)
        if svc is None:
            return unavailable_response(runtime)
        return ok_response(
            data={"ok": True, **svc.get_current_state()},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/swarm/topology/adaptive/regime/<symbol>")
    @login_required
    def swarm_topology_adaptive_regime(symbol: str):
        svc = adaptive_service(runtime)
        if svc is None:
            return unavailable_response(runtime)
        market = (request.args.get("market") or "CN").strip()
        regime = svc.get_regime_for_symbol(symbol, market)
        return ok_response(
            data={"ok": True, "symbol": symbol, "market": market, "regime": regime},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/swarm/topology/adaptive/propose")
    @login_required
    @require_role("can_manage_users")
    def swarm_topology_adaptive_propose():
        svc = adaptive_service(runtime)
        if svc is None:
            return unavailable_response(runtime)
        body = request.get_json(silent=True) or {}
        symbol = body.get("symbol", "600519")
        event_context = body.get("event_context", {})
        return ok_response(
            data={"ok": True, **svc.propose_topology_change(symbol, event_context)},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
