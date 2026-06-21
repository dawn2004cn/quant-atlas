"""Cognitive mesh API routes — Agent-App, Neural Mesh, Hyper-Grid, Canvas."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.core.logger import get_logger
from app.core.registry import register_routes
from app.presentation.api.error_codes import ErrorCode, error_payload
from app.presentation.api.responses import success_response

logger = get_logger(__name__)


def _get_agent_app_registry():
    from app.modules.ai_agent.services.agent_app_runtime import AgentAppRegistry

    return AgentAppRegistry


def _get_neural_mesh(guardian_svc=None):
    from app.modules.system.services.neural_feature_mesh import NeuralFeatureMesh

    return NeuralFeatureMesh(truth_guardian_service=guardian_svc)


def _get_hyper_grid():
    from app.modules.system.services.shared_memory_grid import SharedMemoryHyperGrid

    return SharedMemoryHyperGrid(grid_size_mb=256)


def _get_canvas_service():
    from app.modules.system.services.canvas_predictive_service import CanvasPredictiveService

    return CanvasPredictiveService()


def _error(code: ErrorCode, message: str, *, http_status: int | None = None):
    status = http_status if http_status is not None else code.http_status
    return jsonify(error_payload(code, message)), status


def _register_cognitive_mesh_routes(blueprint: Blueprint, ctx=None) -> None:
    _ = ctx
    cm_bp = Blueprint("cognitive_mesh", __name__, url_prefix="/cognitive-mesh")

    @cm_bp.route("/agent-apps", methods=["GET"])
    def list_agent_apps():
        registry = _get_agent_app_registry()
        apps = registry.get_available()
        return success_response(
            data={
                "apps": [
                    {
                        "app_id": a.app_id,
                        "name": a.name,
                        "description": a.description,
                        "version": a.version,
                        "privilege": a.privilege.name,
                        "icon": a.icon,
                        "tags": a.tags,
                        "config_schema": a.config_schema,
                    }
                    for a in apps
                ],
            },
        )

    @cm_bp.route("/agent-apps/<app_id>/install", methods=["POST"])
    def install_agent_app(app_id: str):
        body = request.get_json(silent=True) or {}
        user_id = body.get("user_id", 1)
        config = body.get("config")
        registry = _get_agent_app_registry()
        try:
            instance = registry.install(app_id, user_id, config)
        except ValueError as exc:
            return _error(ErrorCode.NOT_FOUND, str(exc))
        return success_response(
            data={
                "instance_id": instance.instance_id,
                "app_id": instance.app_id,
                "cpu_quota": instance.cpu_quota,
                "memory_quota_mb": instance.memory_quota_mb,
            },
        )

    @cm_bp.route("/agent-apps/user/<int:user_id>", methods=["GET"])
    def list_installed_apps(user_id: int):
        registry = _get_agent_app_registry()
        instances = registry.get_installed(user_id)
        return success_response(
            data={
                "apps": [
                    {
                        "instance_id": i.instance_id,
                        "app_id": i.app_id,
                        "config": i.config,
                        "status": i.status.name,
                        "cpu_quota": i.cpu_quota,
                        "memory_quota_mb": i.memory_quota_mb,
                        "last_active": i.last_active,
                    }
                    for i in instances
                ],
            },
        )

    @cm_bp.route("/agent-apps/<instance_id>/invoke", methods=["POST"])
    def invoke_agent_app(instance_id: str):
        body = request.get_json(silent=True) or {}
        action = body.get("action", "")
        payload = body.get("payload", {})
        registry = _get_agent_app_registry()
        result = registry.invoke(instance_id, action, payload)
        if result.get("ok"):
            return success_response(data=result)
        return _error(ErrorCode.NOT_FOUND, str(result.get("error", "invoke failed")))

    @cm_bp.route("/agent-apps/<instance_id>/uninstall", methods=["DELETE"])
    def uninstall_agent_app(instance_id: str):
        registry = _get_agent_app_registry()
        ok = registry.uninstall(instance_id)
        return success_response(data={"uninstalled": ok})

    @cm_bp.route("/mesh/crowding", methods=["POST"])
    def detect_crowding():
        body = request.get_json(silent=True) or {}
        mesh = _get_neural_mesh()
        report = mesh.detect_crowding(
            feature_a=body.get("feature_a", ""),
            feature_b=body.get("feature_b", ""),
            ic_series_a=body.get("ic_series_a", []),
            ic_series_b=body.get("ic_series_b", []),
            regime=body.get("regime", "bull"),
        )
        return success_response(
            data={
                "feature_a": report.feature_a,
                "feature_b": report.feature_b,
                "crowding_pct": report.crowding_pct,
                "recommended_replacements": report.recommended_replacements,
                "reason": report.reason,
            },
        )

    @cm_bp.route("/mesh/hygiene-score", methods=["GET"])
    def get_hygiene_score():
        mesh = _get_neural_mesh()
        score = mesh.compute_hygiene_score()
        return success_response(
            data={
                "global_index": score.global_index,
                "sources": score.sources,
                "staleness_days": score.staleness_days,
                "stale_symbols": score.stale_symbols,
            },
        )

    @cm_bp.route("/hyper-grid/nodes", methods=["GET"])
    def list_hyper_grid_nodes():
        grid = _get_hyper_grid()
        return success_response(data={"nodes": grid.sync_all()})

    @cm_bp.route("/hyper-grid/nodes", methods=["POST"])
    def register_hyper_grid_node():
        body = request.get_json(silent=True) or {}
        grid = _get_hyper_grid()
        try:
            node = grid.register_node(
                node_id=body.get("node_id", "default"),
                memory_mb=body.get("memory_mb", 64),
                cpu_cores=body.get("cpu_cores", 1.0),
            )
        except MemoryError as exc:
            return _error(ErrorCode.INTERNAL_ERROR, str(exc), http_status=507)
        return success_response(
            data={
                "node_id": node.node_id,
                "memory_offset": node.memory_offset,
                "memory_size": node.memory_size,
                "cpu_cores": node.cpu_cores,
            },
        )

    @cm_bp.route("/hyper-grid/broadcast", methods=["POST"])
    def broadcast_hyper_grid_message():
        body = request.get_json(silent=True) or {}
        grid = _get_hyper_grid()
        grid.broadcast_message(
            sender=body.get("sender", "system"),
            message_type=body.get("message_type", "update"),
            payload=body.get("payload", {}),
        )
        return success_response()

    @cm_bp.route("/canvas/predict-tools", methods=["POST"])
    def predict_canvas_tools():
        body = request.get_json(silent=True) or {}
        svc = _get_canvas_service()
        tools = svc.predict_tools(
            archetype=body.get("archetype", "novice"),
            symbol=body.get("symbol"),
            context=body.get("context"),
        )
        return success_response(
            data={
                "tools": [
                    {
                        "tool_id": t.tool_id,
                        "tool_name": t.tool_name,
                        "tool_icon": t.tool_icon,
                        "probability": t.probability,
                        "reason": t.reason,
                    }
                    for t in tools
                ],
            },
        )

    @cm_bp.route("/canvas/export-strategy", methods=["POST"])
    def export_canvas_strategy():
        body = request.get_json(silent=True) or {}
        svc = _get_canvas_service()
        export = svc.export_strategy(body)
        return success_response(
            data={
                "name": export.name,
                "logic": export.logic,
                "spec": export.spec,
                "estimated_sharpe": export.estimated_sharpe,
                "risk_level": export.risk_level,
            },
        )

    @cm_bp.route("/dashboard", methods=["GET"])
    def cognitive_mesh_dashboard():
        registry = _get_agent_app_registry()
        apps = registry.get_available()
        mesh = _get_neural_mesh()
        hygiene = mesh.compute_hygiene_score()
        return success_response(
            data={
                "domain": "cognitive_mesh",
                "agent_apps": {
                    "total": len(apps),
                    "by_privilege": {
                        "KERNEL": sum(1 for a in apps if a.privilege.name == "KERNEL"),
                        "SYSTEM": sum(1 for a in apps if a.privilege.name == "SYSTEM"),
                        "USER": sum(1 for a in apps if a.privilege.name == "USER"),
                        "SANDBOX": sum(1 for a in apps if a.privilege.name == "SANDBOX"),
                    },
                },
                "data_hygiene": {
                    "global_index": hygiene.global_index,
                    "sources": hygiene.sources,
                },
                "features": [
                    "agent-app",
                    "neural-mesh",
                    "hyper-grid",
                    "canvas",
                ],
            },
        )

    blueprint.register_blueprint(cm_bp)


@register_routes(name="cognitive_mesh", context="ai_agent", description="Cognitive mesh: Agent-App, Neural Mesh, Hyper-Grid, Canvas")
def register_cognitive_mesh_routes(blueprint: Blueprint, ctx=None) -> None:
    _register_cognitive_mesh_routes(blueprint, ctx)
