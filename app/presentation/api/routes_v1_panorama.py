"""Phase 8.3 Quant-Panorama God-View: full-trace aggregation API."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, request
from flask_login import login_required

from ...core.middleware.request_context import require_authenticated_user_id
from ...core.registry import register_routes
from ..api.common import ok_response, require_ctx_service
from ..api.v1_context import ApiV1Context

DEFAULT_LIMIT = 50


def _uid() -> int:
    return require_authenticated_user_id()


@register_routes(name="panorama", context="system", description="Quant-Panorama God-View")
def register_panorama_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register panorama aggregation routes."""
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/panorama/full-trace")
    @login_required
    def panorama_full_trace() -> Any:
        """Aggregate cross-module DecisionContext traces."""
        user_id = _uid()
        symbol = (request.args.get("symbol") or "").strip()
        limit_str = (request.args.get("limit") or str(DEFAULT_LIMIT)).strip()
        try:
            limit = max(1, min(200, int(limit_str)))
        except (ValueError, TypeError):
            limit = DEFAULT_LIMIT

        uid = "panorama-" + __import__("uuid").uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()
        panorama = {
            "panorama_id": uid,
            "generated_at": now,
            "subject": "user:" + str(user_id),
            "symbol": symbol or None,
        }

        # 1. Arbiter verdicts
        meta = require_ctx_service(ctx, "meta_arbiter_service", required=False)
        if meta:
            try:
                if symbol:
                    panorama["arbiter_verdicts"] = meta.synthesize(symbol)
                else:
                    panorama["arbiter_verdicts"] = meta.list_recent(limit=limit)
            except Exception as e:
                panorama["arbiter_verdicts"] = {"error": str(e)}

        # 2. Evolution status
        evo = require_ctx_service(ctx, "evolution_arbiter_service", required=False)
        if evo:
            try:
                if symbol:
                    regime_result = evo.evaluate_regime(symbol)
                    panorama["evolution_status"] = {
                        "regime_evaluation": regime_result,
                        "arbiter_status": evo.get_status()
                    }
                else:
                    panorama["evolution_status"] = evo.get_status()
            except Exception as e:
                panorama["evolution_status"] = {"error": str(e)}

        # 3. Data truth alerts
        guardian = require_ctx_service(ctx, "data_truth_guardian_service", required=False)
        if guardian:
            try:
                if symbol:
                    panorama["data_truth_alerts"] = guardian.quorum_scan(
                        {"symbols": [symbol], "market": "CN"}
                    )
                else:
                    panorama["data_truth_alerts"] = guardian.get_manifest()
            except Exception as e:
                panorama["data_truth_alerts"] = {"error": str(e)}

        # 4. Module health
        from app.core.registry import check_all_modules_health
        try:
            panorama["module_health"] = check_all_modules_health()
        except Exception as e:
            panorama["module_health"] = {"error": str(e)}

        # 5. Team consensus
        blackboard = require_ctx_service(ctx, "team_blackboard_service", required=False)
        if blackboard:
            try:
                if symbol:
                    consensus = blackboard.synthesize_consensus(team_id=user_id, symbol=symbol)
                    panorama["team_consensus"] = consensus
                else:
                    notes = blackboard.list_notes(team_id=user_id, limit=limit)
                    panorama["team_consensus"] = notes
            except Exception as e:
                panorama["team_consensus"] = {"error": str(e)}

        # 6. System capabilities
        from app.core.capability_registry import get_capability_registry
        try:
            registry = get_capability_registry()
            panorama["system_capabilities"] = registry.stats()
        except Exception as e:
            panorama["system_capabilities"] = {"error": str(e)}

        # 7. Recent events
        from app.application.events import get_event_bus
        try:
            event_bus = get_event_bus()
            recent_events = event_bus.get_history(limit=min(limit, 20))
            panorama["recent_events"] = [
                {
                    "type": event.type.value,
                    "source": event.source,
                    "timestamp": event.timestamp.isoformat(),
                    "payload_keys": list(event.payload.keys()),
                }
                for event in recent_events
            ]
        except Exception as e:
            panorama["recent_events"] = {"error": str(e)}

        # 8. Simulation gateway
        sim_gateway = require_ctx_service(ctx, "simulation_gateway_service", required=False)
        if sim_gateway:
            try:
                panorama["simulation_status"] = sim_gateway.list_scenarios()
            except Exception as e:
                panorama["simulation_status"] = {"error": str(e)}

        panorama["reasoning_trace"] = [
            "Panorama for user:" + str(user_id),
            "symbol=" + (symbol or "all"),
            "generated_at=" + now,
        ]

        return ok_response(data=panorama, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/panorama/battle-room")
    @login_required
    def panorama_battle_room() -> Any:
        """Swarm reasoning studio: team signals + event bus debate timeline."""
        user_id = _uid()
        symbol = (request.args.get("symbol") or "").strip()
        limit = int(request.args.get("limit", 20))

        meta = require_ctx_service(ctx, "meta_arbiter_service", required=False)
        signals: list[dict[str, Any]] = []
        if meta and symbol:
            try:
                signals = meta._collect_team_signals(symbol, "CN", verdict_hint=None)
                signals = [s.model_dump() if hasattr(s, "model_dump") else dict(s) for s in signals[:limit]]
            except Exception as e:
                signals = [{"error": str(e)}]

        events: list[dict[str, Any]] = []
        try:
            from app.application.events import get_event_bus
            bus = get_event_bus()
            recent = bus.get_history(limit=min(limit, 10))
            events = [
                {
                    "type": evt.type.value if hasattr(evt.type, "value") else str(evt.type),
                    "source": evt.source,
                    "timestamp": evt.timestamp.isoformat(),
                    "payload_keys": list(evt.payload.keys()),
                }
                for evt in recent
            ]
        except Exception as e:
            events = [{"error": str(e)}]

        return ok_response(
            data={
                "symbol": symbol,
                "user_id": user_id,
                "team_signals": signals,
                "signal_count": len(signals),
                "debate_timeline": events,
                "event_count": len(events),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/panorama/decision-3d")
    @login_required
    def panorama_decision_3d() -> Any:
        """Reasoning Studio 2.0: 3D decision flow with node coordinates for frontend visualization."""
        _uid()
        symbol = (request.args.get("symbol") or "").strip()

        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        meta = require_ctx_service(ctx, "meta_arbiter_service", required=False)
        if meta and symbol:
            try:
                signals = meta._collect_team_signals(symbol, "CN", verdict_hint=None)
                signal_list = [s.model_dump() if hasattr(s, "model_dump") else dict(s) for s in signals]

                # Build node graph: EvidenceNote -> TeamSignal -> MetaVerdict
                team_nodes = {}
                for i, sig in enumerate(signal_list[:10]):
                    team_fp = sig.get("team_fingerprint", f"team-{i}")
                    (i / max(len(signal_list), 1)) * 360
                    nodes.append({
                        "id": f"team-{team_fp}",
                        "type": "team_signal",
                        "label": f"Team {team_fp[:8]}",
                        "x": 100 * (i % 2),
                        "y": 100 * (i // 2),
                        "z": 0,
                        "confidence": sig.get("confidence", 0.5),
                        "verdict": sig.get("verdict", "neutral"),
                    })
                    team_nodes[team_fp] = sig

                if signal_list:
                    nodes.append({
                        "id": "meta-arbiter",
                        "type": "meta_verdict",
                        "label": "MetaArbiter",
                        "x": 200,
                        "y": 100,
                        "z": 50,
                        "confidence": 0.9,
                    })
                    for sid in team_nodes:
                        edges.append({
                            "source": f"team-{sid}",
                            "target": "meta-arbiter",
                            "type": "consensus_edge",
                        })
            except Exception as e:
                nodes = [{"error": str(e)}]

        return ok_response(
            data={
                "symbol": symbol,
                "decision_graph": {"nodes": nodes, "edges": edges},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/panorama/evolution-tournament")
    @login_required
    def panorama_evolution_tournament() -> Any:
        """Federated Alpha Governance: factor tournament status."""
        from app.domain.alpha.evolution_tournament import get_tournament
        tournament = get_tournament()
        try:
            rankings = tournament.calculate_rankings()
            result = tournament.run_tournament()
            return ok_response(
                data={
                    "strategy_rankings": [{"strategy_id": sid, "score": score} for sid, score in rankings],
                    "promoted": result.promoted,
                    "demoted": result.demoted,
                    "timestamp": result.timestamp.isoformat(),
                },
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )
        except Exception as e:
            return ok_response(data={"error": str(e)}, legacy_alias_key=None, enable_legacy_alias=legacy)
