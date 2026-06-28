"""Swarm topology preset, research graph and user topology routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.v1.swarm_topology._helpers import topology_service, unavailable_response
from app.presentation.api.v1.swarm_topology.runtime import SwarmTopologyRuntime
from app.presentation.api.v1_context import ApiV1Context

from ...decorators import require_role


def register_swarm_topology_core_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: SwarmTopologyRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy

    @blueprint.get("/swarm/topology/presets")
    @login_required
    def swarm_topology_presets():
        svc = topology_service(runtime)
        if svc is None:
            return unavailable_response(runtime)
        return ok_response(data=svc.list_presets(), legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/swarm/topology/presets/<preset_id>")
    @login_required
    def swarm_topology_preset_detail(preset_id: str):
        svc = topology_service(runtime)
        if svc is None:
            return unavailable_response(runtime)
        payload = svc.get_preset(preset_id)
        if not payload.get("ok"):
            raise ValidationError("preset_not_found", details={"preset_id": preset_id})
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/swarm/topology/research-graph")
    @login_required
    def swarm_topology_research_graph():
        svc = topology_service(runtime)
        if svc is None:
            return unavailable_response(runtime)
        payload = svc.get_research_graph_topology()
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "research_graph_unavailable", details=payload)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.put("/swarm/topology/research-graph")
    @login_required
    @require_role("can_manage_users")
    def swarm_topology_research_graph_save():
        svc = topology_service(runtime)
        if svc is None:
            return unavailable_response(runtime)
        body = request.get_json(silent=True) or {}
        topo_body = body.get("topology") if isinstance(body.get("topology"), dict) else body
        payload = svc.save_research_graph_topology(topo_body)
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "save_failed", details=payload)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/swarm/topology/blocks")
    @login_required
    def swarm_topology_blocks():
        svc = topology_service(runtime)
        if svc is None:
            return unavailable_response(runtime)
        return ok_response(data=svc.designer_blocks(), legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/swarm/topology/mine")
    @login_required
    def swarm_topology_mine():
        svc = topology_service(runtime)
        if svc is None:
            return unavailable_response(runtime)
        payload = svc.list_user_topologies(runtime.user_id())
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/swarm/topology/mine/<topology_id>")
    @login_required
    def swarm_topology_mine_detail(topology_id: str):
        svc = topology_service(runtime)
        if svc is None:
            return unavailable_response(runtime)
        payload = svc.get_user_topology(runtime.user_id(), topology_id)
        if not payload.get("ok"):
            raise ValidationError("topology_not_found", details={"topology_id": topology_id})
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/swarm/topology/mine")
    @login_required
    @require_role("can_manage_users")
    def swarm_topology_save():
        svc = topology_service(runtime)
        if svc is None:
            return unavailable_response(runtime)
        body = request.get_json(silent=True) or {}
        payload = svc.save_user_topology(runtime.user_id(), body)
        if not payload.get("ok"):
            raise ValidationError(payload.get("error") or "save_failed", details=payload)
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.post("/swarm/topology/validate")
    @login_required
    @require_role("can_manage_users")
    def swarm_topology_validate():
        svc = topology_service(runtime)
        if svc is None:
            return unavailable_response(runtime)
        body = request.get_json(silent=True) or {}
        from app.domain.topology_schema import SwarmTopologyDescriptor

        try:
            topo = SwarmTopologyDescriptor.model_validate(body)
        except Exception as exc:
            raise ValidationError("invalid_topology", details={"reason": str(exc)}) from exc
        validation = svc.validate_topology(topo)
        return ok_response(
            data={"ok": True, "validation": validation, "topology": topo.model_dump()},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/swarm/topology/generate")
    @login_required
    def swarm_topology_generate():
        svc = topology_service(runtime)
        if svc is None:
            return unavailable_response(runtime)
        regime = (request.args.get("regime") or "default").strip()
        symbol = (request.args.get("symbol") or "").strip()
        return ok_response(
            data=svc.generate_topology(regime, symbol=symbol),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/swarm/topology/propose-agents")
    @login_required
    @require_role("can_manage_users")
    def swarm_topology_propose_agents():
        svc = topology_service(runtime)
        if svc is None:
            return unavailable_response(runtime)
        body = request.get_json(silent=True) or {}
        return ok_response(
            data=svc.propose_agents(body),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/swarm/topology/templates")
    @login_required
    def swarm_topology_templates():
        svc = topology_service(runtime)
        if svc is None:
            return unavailable_response(runtime)
        return ok_response(
            data=svc.list_topology_templates(),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
