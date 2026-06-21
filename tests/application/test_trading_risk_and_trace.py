"""Tests for TradingRiskFacade and decision trace persistence."""

from __future__ import annotations

from app.modules.execution.services.trading_risk_facade import TradingRiskFacade
from app.modules.system.services.ui.decision_trace_service import (
    DecisionTraceService,
    reset_decision_trace_service,
)
from app.domain.dto.decision_context_dto import DecisionContextDTO
from app.infrastructure.risk.risk_gateway import DefaultPositionSizing, DefaultRiskPreFlight


def test_trading_risk_facade_check_order_passes_small_buy():
    facade = TradingRiskFacade(
        preflight=DefaultRiskPreFlight(),
        sizing=DefaultPositionSizing(),
    )
    result = facade.check_order(
        symbol="600519",
        side="buy",
        quantity=100,
        price=10.0,
        total_equity=100_000.0,
        cash_available=100_000.0,
    )
    assert result.allowed is True


def test_trading_risk_facade_kelly_fraction():
    facade = TradingRiskFacade(
        preflight=DefaultRiskPreFlight(),
        sizing=DefaultPositionSizing(),
    )
    fraction = facade.compute_kelly_position(
        win_rate=0.55,
        avg_win=2.0,
        avg_loss=1.0,
        total_equity=100_000.0,
        fraction=0.5,
    )
    assert 0.0 <= fraction <= 1.0


def test_decision_trace_memory_roundtrip():
    reset_decision_trace_service()
    svc = DecisionTraceService(redis_url=None)
    dto = DecisionContextDTO(decision_id="decision_mem001", subject="CN:000001")
    svc.record(dto)
    loaded = svc.get("decision_mem001")
    assert loaded is not None
    payload = svc.trace_payload("decision_mem001")
    assert payload is not None
    assert payload["storage"] == "memory"
