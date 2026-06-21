"""E-1: RiskConfigDTO / PositionSizingDTO for pre-trade preflight."""

from __future__ import annotations

from app.domain.dto.analytics_dto import PositionSizingDTO, RiskConfigDTO
from app.modules.execution.services.pre_trade_preflight_service import PreTradePreflightService


def test_position_sizing_from_atr_rounds_to_lot():
    sizing = PositionSizingDTO.from_atr(
        entry_price=100.0,
        atr=2.5,
        account_equity=1_000_000,
        risk_per_trade=0.02,
    )
    assert sizing.suggested_stop_loss == 95.0
    assert sizing.suggested_take_profit == 107.5
    assert sizing.suggested_quantity >= 100
    assert sizing.max_expected_loss > 0


def test_preflight_uses_risk_config_dto_fields():
    svc = PreTradePreflightService()
    result = svc.preflight(
        symbol="600519",
        direction="BUY",
        price=100,
        quantity=100,
        account_equity=500_000,
        risk_per_trade=0.02,
    )
    assert result.max_trade_amount > 0
    assert result.trade_amount == 10_000
    assert isinstance(result.passed, bool)
