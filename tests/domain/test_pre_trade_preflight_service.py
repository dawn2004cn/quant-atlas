"""Unit tests for PreTradePreflightService — structured pre-trade gate.

Covers app/modules/execution/services/pre_trade_preflight_service.py:
- happy-path pass with valid order
- blocking issues (empty symbol, non-positive qty/price, amount over limit)
- warning when amount near limit
- ATR-based position sizing (stop-loss / take-profit / suggested_qty)
- ATR computation from bars (pure helper)
- direction parsing fallback
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.execution.services.pre_trade_preflight_service import (
    PreTradePreflightService,
)


def _validator(max_amount: float = 1_000_000.0, ok: bool = True):
    """Build a fake validator with a controllable validate() result."""
    v = SimpleNamespace()
    v.max_trade_amount = max_amount
    v.validate = lambda signal: ok
    return v


def _bars(n: int = 15, base: float = 10.0, swing: float = 0.5):
    """Generate n OHLC bars with a fixed high/low swing for deterministic ATR."""
    bars = []
    for i in range(n):
        bars.append({
            "high": base + swing,
            "low": base - swing,
            "close": base,
        })
    return bars


@pytest.fixture
def service() -> PreTradePreflightService:
    """Service with a permissive validator (1M limit, always passes)."""
    return PreTradePreflightService(validator=_validator())


# --- Happy path --------------------------------------------------------------


def test_valid_order_passes(service: PreTradePreflightService):
    """A well-formed order under the limit passes with no blocking issues."""
    r = service.preflight(symbol="600000", direction="buy", price=10.0, quantity=100)
    assert r.passed is True
    assert r.allow_execute is True
    assert r.trade_amount == pytest.approx(1000.0)
    assert not any(i.severity == "blocking" for i in r.issues)


def test_direction_sell_parsed(service: PreTradePreflightService):
    """SELL direction is parsed correctly."""
    r = service.preflight(symbol="600000", direction="sell", price=10.0, quantity=100)
    assert r.passed is True


def test_direction_fallback_for_aliases(service: PreTradePreflightService):
    """Unknown direction strings fall back: LONG→BUY, SHORT→SELL."""
    r_long = service.preflight(symbol="600000", direction="long", price=10.0, quantity=100)
    r_short = service.preflight(symbol="600000", direction="short", price=10.0, quantity=100)
    assert r_long.passed is True
    assert r_short.passed is True


# --- Blocking issues ---------------------------------------------------------


def test_empty_symbol_blocks(service: PreTradePreflightService):
    """Empty symbol after strip produces a blocking 'symbol_required' issue."""
    r = service.preflight(symbol="   ", direction="buy", price=10.0, quantity=100)
    assert r.passed is False
    assert any(i.code == "symbol_required" for i in r.issues)


def test_zero_quantity_blocks(service: PreTradePreflightService):
    """Non-positive quantity blocks execution."""
    r = service.preflight(symbol="600000", direction="buy", price=10.0, quantity=0)
    assert r.passed is False
    assert any(i.code == "quantity_invalid" for i in r.issues)
    assert r.review_queued is True
    assert r.review_decision_id.startswith("preflight_")


def test_zero_price_blocks(service: PreTradePreflightService):
    """Non-positive price blocks execution."""
    r = service.preflight(symbol="600000", direction="buy", price=0, quantity=100)
    assert r.passed is False
    assert any(i.code == "price_invalid" for i in r.issues)


def test_amount_over_limit_blocks():
    """Trade amount exceeding max_trade_amount is blocking."""
    svc = PreTradePreflightService(validator=_validator(max_amount=500.0))
    r = svc.preflight(symbol="600000", direction="buy", price=10.0, quantity=100)  # 1000 > 500
    assert r.passed is False
    assert any(i.code == "trade_amount_exceeds_limit" for i in r.issues)


# --- Warning level -----------------------------------------------------------


def test_amount_near_limit_warns():
    """Amount between 80% and 100% of limit yields a warning, still passes.

    A large portfolio_value keeps the compliance guardrail out of the way so
    the test isolates the near-limit warning logic.
    """
    svc = PreTradePreflightService(validator=_validator(max_amount=1000.0))
    r = svc.preflight(
        symbol="600000", direction="buy", price=9.0, quantity=100,  # 900 = 90%
        portfolio_value=1_000_000.0,
    )
    assert r.passed is True
    assert any(i.code == "trade_amount_near_limit" for i in r.issues)


# --- ATR-based position sizing -----------------------------------------------


def test_atr_sizing_with_market_service():
    """When market_service provides ≥15 bars, ATR sizing populates SL/TP/qty."""
    ms = SimpleNamespace(get_history=lambda sym, n, start, end: _bars(15, base=10.0, swing=0.5))
    svc = PreTradePreflightService(validator=_validator(), market_service=ms)
    r = svc.preflight(
        symbol="600000", direction="buy", price=10.0, quantity=100, account_equity=100_000.0
    )
    assert r.atr_value > 0
    # SL = price - 2*ATR, TP = price + 3*ATR
    assert r.suggested_stop_loss < 10.0
    assert r.suggested_take_profit > 10.0
    assert r.risk_per_trade_pct == pytest.approx(2.0)


def test_atr_zero_without_market_service(service: PreTradePreflightService):
    """Without a market_service, ATR stays 0 and no sizing is produced."""
    r = service.preflight(symbol="600000", direction="buy", price=10.0, quantity=100)
    assert r.atr_value == 0.0
    assert r.suggested_quantity == 0


def test_compute_atr_from_bars_too_few_returns_zero():
    """Fewer than 15 bars yields ATR=0 (insufficient window)."""
    assert PreTradePreflightService._compute_atr_from_bars(_bars(5)) == 0.0


def test_compute_atr_from_bars_deterministic():
    """14-bar ATR with constant 1.0 swing (high-low=2.0) → ATR≈2.0."""
    bars = _bars(20, base=10.0, swing=1.0)  # high=11, low=9 → TR=2 each
    atr = PreTradePreflightService._compute_atr_from_bars(bars)
    assert atr == pytest.approx(2.0, abs=0.01)


def test_compute_atr_from_bars_empty():
    """Empty bar list yields 0.0."""
    assert PreTradePreflightService._compute_atr_from_bars([]) == 0.0
    assert PreTradePreflightService._compute_atr_from_bars(None) == 0.0


# --- Risk score --------------------------------------------------------------


def test_risk_score_reduced_by_blocking(service: PreTradePreflightService):
    """Each blocking issue lowers risk_score; a blocked order scores notably lower."""
    ok = service.preflight(symbol="600000", direction="buy", price=10.0, quantity=100)
    blocked = service.preflight(symbol="   ", direction="buy", price=10.0, quantity=100)
    assert blocked.risk_score < ok.risk_score


def test_hints_present_when_passed(service: PreTradePreflightService):
    """A passing preflight includes at least one hint."""
    r = service.preflight(symbol="600000", direction="buy", price=10.0, quantity=100)
    assert len(r.hints) >= 1
