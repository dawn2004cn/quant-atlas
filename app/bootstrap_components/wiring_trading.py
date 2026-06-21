"""Trading/execution service wiring.

Services for risk, trade plan, portfolio, and execution.

All services are registered via ``register_factory`` / ``register_service``.
"""

from __future__ import annotations

import logging
from typing import Any

from app.bootstrap_components.factory_helpers import zero_arg_service
from app.core.registry import register_factory

logger = logging.getLogger(__name__)

# ── Zero-arg services (lazy import via factory_helpers) ─────────────────

register_factory(
    "risk_alert_service",
    zero_arg_service("app.modules.market_data.services.watchlist_risk_service", "RiskAlertService"),
)

def _make_trade_plan_service(reg: Any) -> Any:
    from app.modules.execution.services.trade_plan_service import TradePlanService

    return TradePlanService(
        market_service=reg.get("market_service"),
        risk_service=reg.get_or_none("risk_service"),
    )


register_factory("trade_plan_service", _make_trade_plan_service)


def _make_selection_source_service(reg):
    from app.modules.data.services.selection_source_service import SelectionSourceService

    return SelectionSourceService(
        strategy_service=reg.get_or_none("strategy_service"),
        qlib_pipeline_service=reg.get_or_none("qlib_pipeline_service"),
        prediction_service=reg.get_or_none("prediction_service"),
        market_service=reg.get_or_none("market_service"),
    )


register_factory("selection_source_service", _make_selection_source_service)

def _make_diagnosis_report_service(reg):
    from app.modules.user.services.user.diagnosis_report_service import DiagnosisReportService
    return DiagnosisReportService(
        ai_analysis_service=reg.get("ai_analysis_service"),
        trade_plan_service=reg.get("trade_plan_service"),
        ai_evidence_service=reg.get("ai_evidence_service"),
        industry_chain_service=reg.get("industry_chain_service"),
    )


register_factory("diagnosis_report_service", _make_diagnosis_report_service)

def _make_portfolio_service(reg: Any) -> Any:
    from app.modules.system.services.helpers.market_data_provider import NullMarketDataProvider, get_market_data_provider
    from app.modules.portfolio_risk.services.portfolio_service import PortfolioApplicationService
    try:
        market_provider = get_market_data_provider()
    except RuntimeError:
        market_provider = NullMarketDataProvider()
    return PortfolioApplicationService(
        market_provider=market_provider,
        local_memory=reg.get_or_none("portfolio_local_memory_service"),
    )


register_factory("portfolio_service", _make_portfolio_service)

register_factory("portfolio_local_memory_service", zero_arg_service("app.modules.system.services.portfolio_local_memory", "PortfolioLocalMemory"))

register_factory(
    "portfolio_trade_service",
    zero_arg_service("app.modules.portfolio_risk.services.portfolio_trade_service", "PortfolioTradeService"),
)

register_factory(
    "simulation_gateway_service",
    zero_arg_service("app.modules.execution.services.simulation_gateway_service", "SimulationGatewayService"),
)

register_factory(
    "self_healing_execution_service",
    zero_arg_service("app.modules.execution.services.self_healing_execution_service", "SelfHealingExecutionService"),
)

register_factory(
    "hyper_simulator_service",
    zero_arg_service("app.modules.execution.services.hyper_simulator_service", "HyperSimulatorService"),
)

register_factory(
    "borderless_execution_service",
    zero_arg_service("app.modules.execution.services.borderless_execution_service", "BorderlessExecutionService"),
)

# ── Complex factories (need settings / session_factory) ─────────────────


def _make_trading_risk_service(reg: Any) -> Any:
    from app.modules.portfolio_risk.services.risk_application_service import RiskApplicationService
    return RiskApplicationService()


register_factory("trading_risk_service", _make_trading_risk_service)
register_factory("risk_application_service", _make_trading_risk_service)


def _make_trading_execution_service(reg: Any) -> Any:
    from app.modules.execution.services.execution_service import ExecutionService
    from app.config import get_settings

    settings = get_settings()
    return ExecutionService(settings=settings)


register_factory("trading_execution_service", _make_trading_execution_service)

register_factory(
    "risk_service",
    zero_arg_service("app.modules.execution.services.trading_risk_facade", "TradingRiskFacade"),
)


def _make_one_click_service(reg: Any) -> Any:
    from app.modules.execution.services.one_click_service import OneClickService

    return OneClickService(
        risk_service=reg.get_or_none("risk_service"),
        strategy_service=reg.get_or_none("strategy_service"),
        mesh_service=reg.get_or_none("wisdom_mesh_service"),
        trade_plan_service=reg.get_or_none("trade_plan_service"),
    )


register_factory("one_click_service", _make_one_click_service)


def _make_active_job_tracker_service(reg: Any) -> Any:
    from app.modules.system.services.system.active_job_tracker_service import ActiveJobTrackerService
    from app.bootstrap_components.wiring_market import _resolve_task_message_store

    return ActiveJobTrackerService(task_message_store=_resolve_task_message_store(reg))


register_factory("active_job_tracker_service", _make_active_job_tracker_service)

