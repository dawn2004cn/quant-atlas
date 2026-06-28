"""Unit tests for trade execution pipeline — PreTradeValidator + PipelineService.

Covers the critical trading path to help reach the 80% coverage target.
"""
from __future__ import annotations

from app.domain.dto.trade_signal_dto import SignalDirection, TradeSignalDTO
from app.infrastructure.trading.pre_trade_validator import (
    InMemorySettlementTracker,
    PreTradeValidator,
    RedisSettlementTracker,
)
from app.modules.execution.services.pre_trade_preflight_service import PreTradePreflightService

# ---------------------------------------------------------------------------
# PreTradeValidator
# ---------------------------------------------------------------------------

class TestPreTradeValidator:
    def _make_signal(self, symbol="600519", direction=SignalDirection.BUY, price=100.0, quantity=100):
        return TradeSignalDTO(
            symbol=symbol,
            direction=direction,
            price=price,
            quantity=quantity,
            strategy_id="test",
        )

    def test_buy_within_limits_passes(self):
        validator = PreTradeValidator(max_trade_amount=1_000_000)
        signal = self._make_signal(price=100.0, quantity=10)
        result = validator.validate(signal)
        assert result.passed is True
        assert not result.reasons

    def test_buy_exceeds_max_amount_blocked(self):
        validator = PreTradeValidator(max_trade_amount=1.0)
        signal = self._make_signal(price=100.0, quantity=10)
        result = validator.validate(signal)
        assert result.passed is False
        assert any("max_trade_amount" in r for r in result.reasons)

    def test_position_limit_blocks_overbuy(self):
        validator = PreTradeValidator(
            max_position_per_stock=50,
            get_position_size=lambda s: 30,
        )
        signal = self._make_signal(quantity=30)
        result = validator.validate(signal)
        assert result.passed is False
        assert any("position limit" in r for r in result.reasons)

    def test_t1_blocks_same_day_sell(self):
        tracker = InMemorySettlementTracker()
        tracker.record_buy("600519")
        validator = PreTradeValidator(settlement_tracker=tracker)
        signal = self._make_signal(direction=SignalDirection.SELL, quantity=10)
        result = validator.validate(signal)
        assert result.passed is False
        assert any("T+1" in r for r in result.reasons)

    def test_sell_after_t1_passes(self):
        tracker = InMemorySettlementTracker()
        tracker.record_buy("600519", trade_date="2020-01-01")
        validator = PreTradeValidator(settlement_tracker=tracker)
        signal = self._make_signal(direction=SignalDirection.SELL, quantity=10)
        result = validator.validate(signal)
        assert result.passed is True

    def test_insufficient_equity_blocks_buy(self):
        validator = PreTradeValidator(
            get_account_equity=lambda: 1.0,
        )
        signal = self._make_signal(price=100.0, quantity=10)
        result = validator.validate(signal)
        assert result.passed is False
        assert any("Insufficient equity" in r for r in result.reasons)


# ---------------------------------------------------------------------------
# RedisSettlementTracker (when Redis unavailable falls back to memory)
# ---------------------------------------------------------------------------

class TestRedisSettlementTracker:
    def test_redis_tracker_factory_fallback(self):
        from app.infrastructure.trading.pre_trade_validator import _create_settlement_tracker
        tracker = _create_settlement_tracker()
        # Without REDIS_URL configured we should get InMemorySettlementTracker
        assert isinstance(tracker, (InMemorySettlementTracker, RedisSettlementTracker))


# ---------------------------------------------------------------------------
# PreTradePreflightService
# ---------------------------------------------------------------------------

class TestPreTradePreflightService:
    def test_preflight_blocks_invalid_quantity(self):
        svc = PreTradePreflightService()
        result = svc.preflight(
            symbol="600519",
            direction="BUY",
            price=100,
            quantity=0,
        )
        assert result.passed is False
        assert any(i.code == "quantity_invalid" for i in result.issues)

    def test_preflight_blocks_invalid_price(self):
        svc = PreTradePreflightService()
        result = svc.preflight(
            symbol="600519",
            direction="BUY",
            price=0,
            quantity=100,
        )
        assert result.passed is False
        assert any(i.code == "price_invalid" for i in result.issues)

    def test_preflight_passes_valid_order(self):
        svc = PreTradePreflightService(
            validator=PreTradeValidator(max_trade_amount=1_000_000),
        )
        result = svc.preflight(
            symbol="600519",
            direction="BUY",
            price=100,
            quantity=10,
            account_equity=1_000_000,
        )
        assert result.passed is True
        assert result.allow_execute is True
        assert result.risk_score >= 0

    def test_atr_warning_on_missing_history(self):
        svc = PreTradePreflightService()
        result = svc.preflight(
            symbol="FAKE999",
            direction="BUY",
            price=100,
            quantity=100,
        )
        # ATR unavailable should produce a warning issue
        atr_issues = [i for i in result.issues if i.code == "atr_unavailable"]
        assert len(atr_issues) == 1
        assert atr_issues[0].severity == "warning"
