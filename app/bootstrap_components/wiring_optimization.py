"""Optimization phase wiring — Dual-Path, Compliance, Complexity Budget, Anti-Decay."""

from __future__ import annotations

from typing import Any

from app.core.logger import get_logger
from app.core.registry import register_factory

logger = get_logger(__name__)


def _make_compliance_service(reg: Any) -> Any:
    from app.modules.system.services.compliance_service import ComplianceService

    return ComplianceService()


def _make_complexity_budget_service(reg: Any) -> Any:
    from app.modules.system.services.complexity_budget_service import ComplexityBudgetService

    return ComplexityBudgetService()


def _make_anti_decay_evolution_service(reg: Any) -> Any:
    from app.modules.system.services.anti_decay_evolution_service import AntiDecayEvolutionService

    return AntiDecayEvolutionService()


def _make_trade_execution_pipeline_service(reg: Any) -> Any:
    from app.modules.execution.services.trade_execution_pipeline_service import TradeExecutionPipelineService

    return TradeExecutionPipelineService(
        compliance_guardrail=reg.get_or_none("compliance_guardrail_service"),
        audit_trail=reg.get_or_none("audit_trail_service"),
    )


def _make_compliance_guardrail_service(reg: Any) -> Any:
    from app.modules.portfolio_risk.services.fund_tier_service import ComplianceGuardrailService

    return ComplianceGuardrailService()


def _make_audit_trail_service(reg: Any) -> Any:
    from app.modules.portfolio_risk.services.fund_tier_service import AuditTrailService

    return AuditTrailService()


def _make_institutional_attribution_service(reg: Any) -> Any:
    from app.modules.portfolio_risk.services.fund_tier_service import InstitutionalAttributionService

    return InstitutionalAttributionService()


def _make_multi_strategy_optimizer_service(reg: Any) -> Any:
    from app.modules.portfolio_risk.services.investment_tier_service import MultiStrategyOptimizerService

    return MultiStrategyOptimizerService()


def _make_pre_trade_preflight_service(reg: Any) -> Any:
    from app.modules.execution.services.pre_trade_preflight_service import PreTradePreflightService

    return PreTradePreflightService(
        validator=None,
        market_service=reg.get_or_none("stock_service"),
    )


register_factory("compliance_service", _make_compliance_service)
register_factory("complexity_budget_service", _make_complexity_budget_service)
register_factory("anti_decay_evolution_service", _make_anti_decay_evolution_service)
register_factory("compliance_guardrail_service", _make_compliance_guardrail_service)
register_factory("audit_trail_service", _make_audit_trail_service)
register_factory("institutional_attribution_service", _make_institutional_attribution_service)
register_factory("multi_strategy_optimizer_service", _make_multi_strategy_optimizer_service)
register_factory("trade_execution_pipeline_service", _make_trade_execution_pipeline_service)
register_factory("pre_trade_preflight_service", _make_pre_trade_preflight_service)


def _make_rbac_service(reg: Any) -> Any:
    from app.modules.system.services.institution_tier_service import RBACService

    return RBACService()


def _make_federated_deployment_service(reg: Any) -> Any:
    from app.modules.system.services.institution_tier_service import FederatedDeploymentService

    return FederatedDeploymentService()


def _make_execution_algo_service(reg: Any) -> Any:
    from app.modules.system.services.institution_tier_service import AdvancedExecutionAlgoService

    return AdvancedExecutionAlgoService()


def _make_market_impact_model_service(reg: Any) -> Any:
    from app.modules.system.services.institution_tier_service import MarketImpactModelService

    return MarketImpactModelService()


register_factory("rbac_service", _make_rbac_service)
register_factory("federated_deployment_service", _make_federated_deployment_service)
register_factory("execution_algo_service", _make_execution_algo_service)
register_factory("market_impact_model_service", _make_market_impact_model_service)


def wire_dual_path_handlers(services: Any | None = None) -> None:
    """Register Fast Path (execution/risk) and Slow Path (AI cognition) handlers."""
    from app.core.dual_path_router import get_dual_path_router

    router = get_dual_path_router()

    def pre_trade_validate(payload: dict) -> dict:
        from app.domain.dto.trade_signal_dto import SignalDirection, TradeSignalDTO
        from app.infrastructure.trading.pre_trade_validator import PreTradeValidator

        signal_data = payload.get("signal", {})
        if not signal_data:
            return {"valid": False, "error": "signal_required"}
        direction = signal_data.get("direction", SignalDirection.BUY)
        if isinstance(direction, str):
            direction = SignalDirection(direction.upper())
        signal = TradeSignalDTO.model_validate(
            {
                "symbol": str(signal_data.get("symbol", "")),
                "direction": direction,
                "price": float(signal_data.get("price", 0)),
                "quantity": int(signal_data.get("quantity", 0)),
                "strategy_id": str(signal_data.get("strategy_id", "fast_path")),
            }
        )
        validator = PreTradeValidator(
            max_trade_amount=float(payload.get("max_trade_amount", 1_000_000)),
            max_position_per_stock=int(payload.get("max_position_per_stock", 0)),
        )
        ok = validator.validate(signal)
        return {"valid": ok, "symbol": signal.symbol}

    def copy_trade_execute(payload: dict) -> dict:
        from app.modules.execution.services.trade_execution_pipeline_service import TradeExecutionPipelineService

        pipeline = TradeExecutionPipelineService()
        result = pipeline.execute(
            user_id=int(payload.get("follower_id", 0)),
            symbol=str(payload.get("symbol", "")),
            action=str(payload.get("action", "buy")),
            quantity=int(payload.get("quantity", 0)),
            price=float(payload.get("price", 0)),
            sector=str(payload.get("sector", "unknown")),
            portfolio_value=float(payload.get("portfolio_value", 1_000_000)),
            skip_impact=True,
            skip_rbac=True,
        )
        if not result.ok:
            return {"executed": False, "stage": result.stage, "violations": result.violations}
        return {
            "executed": True,
            "order_id": result.order_id,
            "snapshot_id": result.snapshot_id,
            **result.execution,
        }

    def compliance_guardrail_check(payload: dict) -> dict:
        from app.modules.portfolio_risk.services.fund_tier_service import ComplianceGuardrailService

        svc = ComplianceGuardrailService()
        blacklist = payload.get("blacklist")
        if isinstance(blacklist, list):
            svc.set_blacklist(blacklist)
        result = svc.check_order(
            symbol=str(payload.get("symbol", "")),
            sector=str(payload.get("sector", "unknown")),
            order_value=float(payload.get("order_value", 0)),
            portfolio_value=float(payload.get("portfolio_value", 1_000_000)),
            current_position_pct=float(payload.get("current_position_pct", 0)),
            current_sector_pct=float(payload.get("current_sector_pct", 0)),
        )
        return {"passed": result.passed, "violations": result.violations, "checks": result.checks}

    def trade_pipeline_execute(payload: dict) -> dict:
        from app.modules.execution.services.trade_execution_pipeline_service import TradeExecutionPipelineService

        pipeline = TradeExecutionPipelineService()
        result = pipeline.execute(
            user_id=int(payload.get("user_id", 0)),
            symbol=str(payload.get("symbol", "")),
            action=str(payload.get("action", "buy")),
            quantity=int(payload.get("quantity", 0)),
            price=float(payload.get("price", 0)),
            sector=str(payload.get("sector", "unknown")),
            portfolio_value=float(payload.get("portfolio_value", 1_000_000)),
            current_position_pct=float(payload.get("current_position_pct", 0)),
            current_sector_pct=float(payload.get("current_sector_pct", 0)),
            strategy_id=str(payload.get("strategy_id", "pipeline")),
            ai_evidence=payload.get("ai_evidence"),
            factor_values=payload.get("factor_values"),
            skip_impact=bool(payload.get("skip_impact", False)),
        )
        return result.__dict__

    def ai_mentor_observe(payload: dict) -> None:
        from app.modules.user.services.retail_tier_service import AiMentorService

        svc = AiMentorService()
        advice = svc.advise(
            symbol=str(payload.get("symbol", "")),
            factor_values=payload.get("factors", {}),
        )
        logger.info("Slow Path mentor advice: %s %s", advice.symbol, advice.action)

    def prompt_evolution_observe(payload: dict) -> None:
        try:
            from app.modules.ai_agent.services.prompt_evolution_service import PromptEvolutionService

            svc = PromptEvolutionService()
            if hasattr(svc, "record_feedback"):
                svc.record_feedback(payload)
        except Exception as exc:
            logger.debug("Slow Path prompt evolution skipped: %s", exc)

    def memory_fabric_observe(payload: dict) -> None:
        try:
            from app.core.mesh.memory_fabric import get_memory_fabric

            fabric = get_memory_fabric()
            if hasattr(fabric, "index"):
                fabric.index(payload)
        except Exception as exc:
            logger.debug("Slow Path memory fabric skipped: %s", exc)

    router.register_fast_handler("pre_trade_validate", pre_trade_validate)
    router.register_fast_handler("compliance_guardrail_check", compliance_guardrail_check)
    router.register_fast_handler("trade_pipeline_execute", trade_pipeline_execute)
    router.register_fast_handler("copy_trade_execute", copy_trade_execute)
    router.register_slow_handler("ai_mentor", ai_mentor_observe)
    router.register_slow_handler("prompt_evolution", prompt_evolution_observe)
    router.register_slow_handler("memory_fabric_index", memory_fabric_observe)

    logger.info("Dual-Path handlers registered (4 fast, 3 slow)")


def wire_optimization_services(services: Any | None = None) -> None:
    """Bootstrap hook: dual-path handlers + optional complexity audit."""
    wire_dual_path_handlers(services)
    try:
        from app.modules.system.services.complexity_budget_service import ComplexityBudgetService

        budget = ComplexityBudgetService()
        registry = None
        if services is not None:
            try:
                from app.bootstrap_components.service_wiring import _get_registry

                registry = _get_registry()
            except Exception:
                registry = None
        wiring = budget.validate_wiring(registry)
        if not wiring.get("ok", True):
            logger.warning("Wiring validation issues: %s", wiring.get("errors"))
        elif wiring.get("factory_count"):
            logger.info(
                "Wiring OK: %d factories registered, %d resolved",
                wiring.get("factory_count", 0),
                wiring.get("factories_resolved", 0),
            )
    except Exception as exc:
        logger.debug("Complexity budget wiring check skipped: %s", exc)


__all__ = [
    "wire_dual_path_handlers",
    "wire_optimization_services",
]
