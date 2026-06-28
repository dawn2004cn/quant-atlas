"""User Tier API — Fund manager tier routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required, current_user

from app.core.logger import get_logger
from app.core.rbac_guard import require_rbac
from app.core.registry import register_routes
from app.presentation.api.v1.user_tiers._http import tier_success

logger = get_logger(__name__)

_bp = Blueprint("fund", __name__)


def _get_services():
    from app.modules.portfolio_risk.services.fund_tier_service import (
        InstitutionalAttributionService, ComplianceGuardrailService, AuditTrailService, MasterSlaveService,
    )
    return InstitutionalAttributionService(), ComplianceGuardrailService(), AuditTrailService(), MasterSlaveService()


# ── Attribution ──

@_bp.post("/fund/attribution/brinson")
@login_required
def fund_brinson():
    data = request.get_json(silent=True) or {}
    svc, _, _, _ = _get_services()
    result = svc.brinson_attribution(
        portfolio_id=str(data.get("portfolio_id", "")),
        portfolio_weights=data.get("portfolio_weights", {}),
        portfolio_returns=data.get("portfolio_returns", {}),
        benchmark_weights=data.get("benchmark_weights", {}),
        benchmark_returns=data.get("benchmark_returns", {}),
    )
    return tier_success(result)


@_bp.post("/fund/attribution/factor")
@login_required
def fund_factor_attribution():
    """Barra-style factor attribution."""
    data = request.get_json(silent=True) or {}
    svc, _, _, _ = _get_services()
    result = svc.factor_attribution(
        portfolio_id=str(data.get("portfolio_id", "")),
        portfolio_returns=data.get("portfolio_returns", {}),
        factor_exposures=data.get("factor_exposures", {}),
        factor_returns=data.get("factor_returns", {}),
    )
    return tier_success(result)


@_bp.post("/fund/attribution/multi-period")
@login_required
def fund_multi_period_attribution():
    """Multi-period Brinson attribution."""
    data = request.get_json(silent=True) or {}
    svc, _, _, _ = _get_services()
    result = svc.multi_period_attribution(
        portfolio_id=str(data.get("portfolio_id", "")),
        periods=data.get("periods", []),
    )
    return tier_success(result)


# ── Compliance ──

@_bp.post("/fund/compliance/check")
@login_required
def fund_compliance_check():
    data = request.get_json(silent=True) or {}
    _, svc, _, _ = _get_services()
    result = svc.check_order(
        symbol=str(data.get("symbol", "")),
        sector=str(data.get("sector", "")),
        order_value=float(data.get("order_value", 0)),
        portfolio_value=float(data.get("portfolio_value", 1)),
        current_position_pct=float(data.get("current_position_pct", 0)),
        current_sector_pct=float(data.get("current_sector_pct", 0)),
    )
    return tier_success(result)


@_bp.post("/fund/compliance/summary")
@login_required
def fund_compliance_summary():
    """Run all compliance checks and return summary."""
    data = request.get_json(silent=True) or {}
    _, svc, _, _ = _get_services()
    result = svc.get_compliance_summary(
        symbol=str(data.get("symbol", "")),
        sector=str(data.get("sector", "")),
        order_value=float(data.get("order_value", 0)),
        portfolio_value=float(data.get("portfolio_value", 1)),
        current_position_pct=float(data.get("current_position_pct", 0)),
        current_sector_pct=float(data.get("current_sector_pct", 0)),
        recent_trades_last_hour=int(data.get("recent_trades_last_hour", 0)),
        daily_pnl=float(data.get("daily_pnl", 0)),
    )
    return tier_success(result)


# ── Audit ──

@_bp.post("/fund/audit/snapshot")
@login_required
def fund_audit_snapshot():
    data = request.get_json(silent=True) or {}
    _, _, svc, _ = _get_services()
    snapshot = svc.record_snapshot(
        order_id=str(data.get("order_id", "")),
        user_id=current_user.id,
        symbol=str(data.get("symbol", "")),
        action=str(data.get("action", "")),
        quantity=int(data.get("quantity", 0)),
        price=float(data.get("price", 0)),
        ai_evidence=data.get("ai_evidence"),
        factor_values=data.get("factor_values"),
        risk_assessment=data.get("risk_assessment"),
        compliance_result=data.get("compliance_result"),
    )
    return tier_success(snapshot)


@_bp.get("/fund/audit/<order_id>")
@login_required
def fund_audit_query(order_id: str):
    _, _, svc, _ = _get_services()
    snapshots = svc.get_snapshots(order_id)
    return tier_success([s for s in snapshots])


@_bp.get("/fund/audit/<order_id>/verify")
@login_required
def fund_audit_verify(order_id: str):
    """Verify tamper-evident hash chain for an order's audit snapshots."""
    _, _, svc, _ = _get_services()
    result = svc.verify_order_chain(order_id)
    return tier_success(result, meta={"valid": result.valid})


@_bp.get("/fund/audit/chain/verify")
@login_required
def fund_audit_verify_global():
    """Verify integrity of the full audit trail hash chain."""
    _, _, svc, _ = _get_services()
    result = svc.verify_global_chain()
    return tier_success(result, meta={"valid": result.valid})


@_bp.get("/fund/audit/export")
@login_required
def fund_audit_export():
    """Export audit log as JSON or CSV."""
    order_id = request.args.get("order_id")
    fmt = request.args.get("format", "json")
    _, _, svc, _ = _get_services()
    log = svc.export_audit_log(order_id=order_id, format=fmt)
    if fmt == "csv":
        from flask import Response
        return Response(log, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=audit_log.csv"})
    return tier_success(log)


@_bp.get("/fund/audit/export/<order_id>")
@login_required
def fund_audit_export_by_order(order_id: str):
    svc, _, _, _ = _get_services()
    fmt = request.args.get("format", "json")
    result = svc.export_audit_log(order_id=order_id, format=fmt)
    return tier_success(result)


# ── Master-Slave ──

@_bp.post("/fund/master-slave/register")
@login_required
def fund_master_slave_register():
    data = request.get_json(silent=True) or {}
    _, _, _, svc = _get_services()
    account = svc.register_slave(
        master_id=str(data.get("master_id", str(current_user.id))),
        name=str(data.get("name", "")),
        capital=float(data.get("capital", 0)),
        allocation_pct=float(data.get("allocation_pct", 100)),
    )
    return tier_success(account)


@_bp.post("/fund/master-slave/execute")
@login_required
def fund_master_slave_execute():
    data = request.get_json(silent=True) or {}
    _, _, _, svc = _get_services()
    results = svc.execute_master_trade(
        master_id=str(data.get("master_id", str(current_user.id))),
        symbol=str(data.get("symbol", "")),
        action=str(data.get("action", "")),
        quantity=int(data.get("quantity", 0)),
        price=float(data.get("price", 0)),
    )
    return tier_success(results)


# ── Trade Pipeline ──

@_bp.post("/fund/trade/pipeline")
@login_required
@require_rbac("order", "execute")
def fund_trade_pipeline():
    """Phase II: unified compliance → risk → audit → execution pipeline."""
    data = request.get_json(silent=True) or {}
    from app.modules.execution.services.trade_execution_pipeline_service import TradeExecutionPipelineService
    pipeline = TradeExecutionPipelineService()
    result = pipeline.execute(
        user_id=current_user.id,
        symbol=str(data.get("symbol", "")),
        action=str(data.get("action", "buy")),
        quantity=int(data.get("quantity", 0)),
        price=float(data.get("price", 0)),
        sector=str(data.get("sector", "unknown")),
        portfolio_value=float(data.get("portfolio_value", 1_000_000)),
        current_position_pct=float(data.get("current_position_pct", 0)),
        current_sector_pct=float(data.get("current_sector_pct", 0)),
        strategy_id=str(data.get("strategy_id", "fund")),
        ai_evidence=data.get("ai_evidence"),
        factor_values=data.get("factor_values"),
        skip_impact=bool(data.get("skip_impact", False)),
    )
    return tier_success(result, meta={"accepted": result.ok})


# ── Registration ──

@register_routes(name="fund", context="system", description="Fund manager tier: Attribution, Compliance, Audit, Master-Slave, Trade Pipeline")
def register_fund_routes(blueprint, ctx) -> None:
    blueprint.register_blueprint(_bp, url_prefix="/user-tiers")
