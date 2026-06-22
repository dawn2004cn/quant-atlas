"""User Tier API — Institution tier routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required, current_user

from app.core.rbac_guard import require_rbac
from app.core.registry import register_routes
from app.presentation.api.decorators import require_role
from app.presentation.api.v1.user_tiers._http import tier_not_found, tier_success

_bp = Blueprint("institution", __name__)


def _get_services():
    from app.modules.system.services.institution_tier_service import (
        MarketImpactModelService, AdvancedExecutionAlgoService, FederatedDeploymentService, RBACService,
    )
    return MarketImpactModelService(), AdvancedExecutionAlgoService(), FederatedDeploymentService(), RBACService()


# ── Market Impact ──

@_bp.post("/institution/impact/forecast")
@login_required
def institution_impact_forecast():
    data = request.get_json(silent=True) or {}
    svc, _, _, _ = _get_services()
    forecast = svc.forecast(
        symbol=str(data.get("symbol", "")),
        order_value_usd=float(data.get("order_value_usd", 0)),
        side=str(data.get("side", "buy")),
    )
    return tier_success(forecast)


@_bp.post("/institution/impact/almgren-chriss")
@login_required
def institution_impact_almgren():
    data = request.get_json(silent=True) or {}
    svc, _, _, _ = _get_services()
    result = svc.forecast_almgren_chriss(
        symbol=str(data.get("symbol", "")),
        order_value_usd=float(data.get("order_value_usd", 0)),
        side=str(data.get("side", "buy")),
        price=float(data.get("price", 100)),
        spread_bps=float(data.get("spread_bps", 5)),
    )
    return tier_success(result)


@_bp.post("/institution/impact/multi-asset")
@login_required
def institution_impact_multi():
    data = request.get_json(silent=True) or {}
    svc, _, _, _ = _get_services()
    orders = data.get("orders", [])
    result = svc.forecast_multi_asset(orders)
    return tier_success(result)


# ── Execution Algorithms ──

@_bp.post("/institution/execution/pov")
@login_required
@require_rbac("order", "execute")
def institution_execution_pov():
    data = request.get_json(silent=True) or {}
    _, svc, _, _ = _get_services()
    schedule = svc.generate_pov(
        symbol=str(data.get("symbol", "")),
        side=str(data.get("side", "buy")),
        total_quantity=int(data.get("quantity", 0)),
        participation_rate=float(data.get("participation_rate", 0.1)),
    )
    return tier_success(schedule)


@_bp.post("/institution/execution/vwap")
@login_required
@require_rbac("order", "execute")
def institution_execution_vwap():
    data = request.get_json(silent=True) or {}
    _, svc, _, _ = _get_services()
    schedule = svc.generate_vwap(
        symbol=str(data.get("symbol", "")),
        side=str(data.get("side", "buy")),
        total_quantity=int(data.get("quantity", 0)),
        num_slices=int(data.get("num_slices", 20)),
    )
    return tier_success(schedule)


@_bp.post("/institution/execution/twap")
@login_required
@require_rbac("order", "execute")
def institution_execution_twap():
    data = request.get_json(silent=True) or {}
    _, svc, _, _ = _get_services()
    schedule = svc.generate_twap(
        symbol=str(data.get("symbol", "")),
        side=str(data.get("side", "buy")),
        total_quantity=int(data.get("quantity", 0)),
        num_slices=int(data.get("num_slices", 20)),
        interval_minutes=int(data.get("interval_minutes", 5)),
    )
    return tier_success(schedule)


@_bp.post("/institution/execution/iceberg")
@login_required
@require_rbac("order", "execute")
def institution_execution_iceberg():
    data = request.get_json(silent=True) or {}
    _, svc, _, _ = _get_services()
    schedule = svc.generate_iceberg(
        symbol=str(data.get("symbol", "")),
        side=str(data.get("side", "buy")),
        total_quantity=int(data.get("quantity", 0)),
        display_quantity=int(data.get("display_quantity", 100)),
        variance_pct=float(data.get("variance_pct", 0.1)),
    )
    return tier_success(schedule)


@_bp.post("/institution/execution/adaptive")
@login_required
def institution_execution_adaptive():
    data = request.get_json(silent=True) or {}
    _, svc, _, _ = _get_services()
    result = svc.generate_adaptive(
        symbol=str(data.get("symbol", "")),
        side=str(data.get("side", "buy")),
        total_quantity=int(data.get("total_quantity", 1000)),
        impact_bps=float(data.get("impact_bps", 0)),
        urgency=str(data.get("urgency", "normal")),
    )
    return tier_success(result)


@_bp.post("/institution/execution/shortfall")
@login_required
def institution_execution_shortfall():
    data = request.get_json(silent=True) or {}
    _, svc, _, _ = _get_services()
    result = svc.generate_implementation_shortfall(
        symbol=str(data.get("symbol", "")),
        side=str(data.get("side", "buy")),
        total_quantity=int(data.get("total_quantity", 1000)),
        price=float(data.get("price", 100)),
        urgency=str(data.get("urgency", "normal")),
    )
    return tier_success(result)


# ── Federated Learning ──

@_bp.post("/institution/federated/update")
@login_required
def institution_federated_update():
    data = request.get_json(silent=True) or {}
    _, _, svc, _ = _get_services()
    update = svc.receive_update(
        node_id=str(data.get("node_id", "")),
        model_name=str(data.get("model_name", "")),
        weight_updates=data.get("weight_updates", {}),
        performance_delta=float(data.get("performance_delta", 0)),
    )
    return tier_success(update)


@_bp.get("/institution/federated/aggregate/<model_name>")
@login_required
def institution_federated_aggregate(model_name: str):
    _, _, svc, _ = _get_services()
    aggregated = svc.aggregate_updates(model_name)
    return tier_success(aggregated)


@_bp.post("/institution/federated/aggregate/<model_name>/round")
@login_required
@require_rbac("strategy", "write")
def institution_federated_round(model_name: str):
    """Run FedAvg round with min-node guard and persist aggregated model."""
    _, _, svc, _ = _get_services()
    result = svc.run_fedavg_round(model_name)
    return tier_success(result, meta={"accepted": result.ok})


@_bp.get("/institution/federated/status")
@login_required
def institution_federated_status():
    _, _, svc, _ = _get_services()
    status = svc.get_cluster_status()
    return tier_success(status)


@_bp.post("/institution/federated/nodes/<node_id>/heartbeat")
@login_required
def institution_federated_heartbeat(node_id: str):
    data = request.get_json(silent=True) or {}
    _, _, svc, _ = _get_services()
    node = svc.heartbeat(node_id, metadata=data.get("metadata"))
    if node is None:
        return tier_not_found("node_not_found")
    return tier_success(node)


@_bp.get("/institution/federated/models/<model_name>")
@login_required
def institution_federated_model(model_name: str):
    _, _, svc, _ = _get_services()
    model = svc.get_aggregated_model(model_name)
    if model is None:
        return tier_not_found("model_not_found")
    return tier_success(model)


@_bp.get("/institution/federated/config")
@login_required
def institution_federated_config_get():
    _, _, svc, _ = _get_services()
    return tier_success(svc.get_deployment_config())


@_bp.post("/institution/federated/config")
@login_required
@require_rbac("strategy", "write")
def institution_federated_config_set():
    data = request.get_json(silent=True) or {}
    _, _, svc, _ = _get_services()
    config = svc.set_deployment_config(data)
    return tier_success(config)


@_bp.post("/institution/federated/nodes")
@login_required
@require_rbac("strategy", "write")
def institution_federated_register_node():
    data = request.get_json(silent=True) or {}
    _, _, svc, _ = _get_services()
    node = svc.register_node(
        node_id=str(data.get("node_id", "")),
        name=str(data.get("name", "")),
        mode=str(data.get("mode", "federated")),
    )
    return tier_success(node)


@_bp.get("/institution/federated/nodes")
@login_required
def institution_federated_list_nodes():
    _, _, svc, _ = _get_services()
    return tier_success(svc.list_nodes())


@_bp.get("/institution/federated/export/<model_name>")
@login_required
def institution_federated_export(model_name: str):
    _, _, svc, _ = _get_services()
    fmt = request.args.get("format", "json")
    result = svc.export_model(model_name, export_format=fmt)
    if result is None:
        return tier_not_found("model_not_found")
    return tier_success(result)


@_bp.post("/institution/federated/import")
@login_required
@require_rbac("strategy", "write")
def institution_federated_import():
    data = request.get_json(silent=True) or {}
    _, _, svc, _ = _get_services()
    model_name = str(data.get("model_name", ""))
    export_data = data.get("export_data", {})
    ok = svc.import_model(model_name, export_data)
    return tier_success({"accepted": ok})


# ── RBAC ──

@_bp.post("/institution/rbac/assign")
@login_required
@require_role("can_manage_users")
def institution_rbac_assign():
    data = request.get_json(silent=True) or {}
    _, _, _, svc = _get_services()
    assignment = svc.assign_role(
        user_id=int(data.get("user_id", current_user.id)),
        role_id=str(data.get("role_id", "researcher")),
    )
    return tier_success({"user_id": assignment.user_id, "role_id": assignment.role_id})


@_bp.get("/institution/rbac/check/<resource>/<permission>")
@login_required
def institution_rbac_check(resource: str, permission: str):
    _, _, _, svc = _get_services()
    allowed = svc.check_permission(current_user.id, resource, permission)
    return tier_success({"allowed": allowed})


@_bp.post("/institution/rbac/check-multi")
@login_required
def institution_rbac_check_multi():
    data = request.get_json(silent=True) or {}
    _, _, _, svc = _get_services()
    resources = data.get("resources", {})
    result = svc.check_multi_resource(current_user.id, resources)
    return tier_success(result)


@_bp.get("/institution/rbac/roles")
@login_required
def institution_rbac_roles():
    _, _, _, svc = _get_services()
    roles = svc.list_roles()
    return tier_success(roles)


@_bp.get("/institution/rbac/me")
@login_required
def institution_rbac_me():
    _, _, _, svc = _get_services()
    assignment = svc.get_user_assignment(current_user.id)
    return tier_success(assignment or {"user_id": current_user.id, "role_id": None})


@_bp.get("/institution/rbac/permissions")
@login_required
def institution_rbac_permissions():
    _, _, _, svc = _get_services()
    result = svc.list_user_permissions(current_user.id)
    return tier_success(result)


@_bp.post("/institution/rbac/audit")
@login_required
@require_rbac("user", "admin")
def institution_rbac_audit():
    data = request.get_json(silent=True) or {}
    _, _, _, svc = _get_services()
    target_user = int(data.get("target_user", 0))
    action = str(data.get("action", ""))
    result = svc.audit_change(current_user.id, target_user, action, data.get("detail"))
    return tier_success(result)


# ── Registration ──

@register_routes(name="institution", context="system", description="Institution tier: Market Impact, Execution Algorithms, Federated Learning, RBAC")
def register_institution_routes(blueprint, ctx) -> None:
    blueprint.register_blueprint(_bp, url_prefix="/user-tiers")
