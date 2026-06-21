"""Tests for TradingWorkflow — signal generation, risk check, order execution."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.application.workflows.trading_workflow import TradingWorkflow
from app.core.event_bus import TradeExecutedEvent, get_event_bus
from app.domain.enums import MarketCode
from app.domain.services.signal_generation_service import (
    GeneratedSignal,
    SignalAggregator,
    SignalConfig,
    SignalGenerationService,
    SignalSource,
)
from app.domain.services.trading_policy_service import (
    PolicyResult,
    PolicyViolation,
    TradingAction,
    TradingPolicy,
    TradingPolicyService,
)


# ── Helpers ────────────────────────────────────────────────────────────────


def _mock_registry(
    bars: list[dict] | None = None,
    exec_result: dict | None = None,
) -> MagicMock:
    """Return a MagicMock CapabilityRegistry that yields controlled results."""
    reg = MagicMock()
    reg.execute.side_effect = lambda name, **kw: (
        (bars, "fetched_bars") if name == "fetch_bars"
        else (exec_result or {"status": "executed", "order_id": "mock_ord_1"}, "ok")
        if name == "execute_order"
        else (None, "unknown_capability")
    )
    reg.available = ["fetch_bars", "execute_order"]
    return reg


# ── Step 1: Signal Generation ─────────────────────────────────────────────


def test_generate_signal_with_bars() -> None:
    """Bars → indicators → bullish signal."""
    bars = [
        {"close": 100.0 + i * 0.5} for i in range(30)
    ]
    reg = _mock_registry(bars=bars)

    wf = TradingWorkflow(
        workflow_id="wf_sig_001",
        symbol="600519",
        market=MarketCode.CN,
        strategy_name="ma_cross",
        capability_registry=reg,
    )
    wf.start()

    step_data = wf.get_evidence()[-1] if wf.get_evidence() else {}
    signal_result = wf._step_generate_signal(MagicMock(data={}))

    assert signal_result["signal_type"] in ("buy", "sell", "hold")
    assert signal_result["bar_count"] == 30
    assert signal_result["note"] == "fetched_bars"
    assert abs(signal_result["indicators"]["close"] - 114.5) < 0.01
    assert signal_result["indicators"]["ma5"] > 0


def test_generate_signal_no_bars() -> None:
    """No bars → empty indicators → hold signal."""
    reg = _mock_registry(bars=None)

    wf = TradingWorkflow(
        workflow_id="wf_sig_002",
        symbol="000001",
        market=MarketCode.CN,
        capability_registry=reg,
    )
    wf.start()

    result = wf._step_generate_signal(MagicMock(data={}))
    assert result["signal_type"] == "hold"
    assert result["bar_count"] == 0
    assert result["indicators"] == {}


def test_generate_signal_fetch_fails() -> None:
    """fetch_bars raises → note contains error."""
    reg = MagicMock()
    reg.execute.side_effect = KeyError("capability not found")

    wf = TradingWorkflow(
        workflow_id="wf_sig_003",
        symbol="600519",
        market=MarketCode.CN,
        capability_registry=reg,
    )
    wf.start()

    result = wf._step_generate_signal(MagicMock(data={}))
    assert result["bar_count"] == 0
    assert "fetch_error" in result["note"]


# ── Step 2: Risk Check ────────────────────────────────────────────────────


def test_risk_check_skip_hold() -> None:
    """Hold signal → risk check skipped."""
    wf = TradingWorkflow(
        workflow_id="wf_risk_001",
        symbol="600519",
        market=MarketCode.CN,
    )
    wf.start()

    result = wf._step_risk_check(MagicMock(data={"generate_signal": {"signal_type": "hold"}}))
    assert result["risk_action"] == "skip_hold"
    assert result["violations"] == []


def test_risk_check_buy_allowed() -> None:
    """Strong buy signal within policy limits → allowed."""
    policy = TradingPolicy(
        max_single_trade=0.10,
        max_position_size=0.50,
    )
    wf = TradingWorkflow(
        workflow_id="wf_risk_002",
        symbol="600519",
        market=MarketCode.CN,
        trading_policy=policy,
        portfolio_value=1_000_000,
    )
    wf.start()

    result = wf._step_risk_check(
        MagicMock(data={
            "generate_signal": {"signal_type": "buy", "confidence": 0.8},
        }),
    )
    assert result["risk_action"] == "allow"
    assert result["is_allowed"] is True


def test_risk_check_buy_blocked_restricted_stock() -> None:
    """Restricted stock → blocked."""
    policy = TradingPolicy(restricted_stocks=("600519",))
    wf = TradingWorkflow(
        workflow_id="wf_risk_003",
        symbol="600519",
        market=MarketCode.CN,
        trading_policy=policy,
    )
    wf.start()

    result = wf._step_risk_check(
        MagicMock(data={
            "generate_signal": {"signal_type": "buy", "confidence": 0.9},
        }),
    )
    assert result["risk_action"] == "block"
    assert PolicyViolation.RESTRICTED_STOCK in result["violations"]


# ── Step 3: Order Execution ───────────────────────────────────────────────


def test_execute_order_skipped_on_block() -> None:
    """Blocked risk check → order skipped."""
    reg = _mock_registry()
    wf = TradingWorkflow(
        workflow_id="wf_exec_001",
        symbol="600519",
        market=MarketCode.CN,
        capability_registry=reg,
    )
    wf.start()

    result = wf._step_execute_order(
        MagicMock(data={
            "risk_check": {"risk_action": "block"},
            "generate_signal": {"signal_type": "buy"},
        }),
    )
    assert result["status"] == "skipped"
    assert "risk_action=block" in result["reason"]


def test_execute_order_skipped_on_hold() -> None:
    """Hold signal → order skipped."""
    reg = _mock_registry()
    wf = TradingWorkflow(
        workflow_id="wf_exec_002",
        symbol="600519",
        market=MarketCode.CN,
        capability_registry=reg,
    )
    wf.start()

    result = wf._step_execute_order(
        MagicMock(data={
            "risk_check": {"risk_action": "skip_hold"},
            "generate_signal": {"signal_type": "hold"},
        }),
    )
    assert result["status"] == "skipped"


def test_execute_order_simulated() -> None:
    """Buy signal passes risk → simulated order with provenance."""
    reg = _mock_registry(exec_result={"status": "executed", "order_id": "sim_001"})
    wf = TradingWorkflow(
        workflow_id="wf_exec_003",
        symbol="600519",
        market=MarketCode.CN,
        capability_registry=reg,
    )
    wf.start()

    result = wf._step_execute_order(
        MagicMock(data={
            "risk_check": {"risk_action": "allow", "trade_value": 50000},
            "generate_signal": {"signal_type": "buy", "indicators": {"close": 100}},
        }),
    )
    assert result["status"] in ("executed", "simulated")
    assert result["provenance_id"].startswith("prov_")
    assert result["direction"] == "buy"


def test_execute_order_capability_fallback_to_simulated() -> None:
    """execute_order capability missing → falls back to simulated."""
    reg = MagicMock()
    reg.execute.side_effect = KeyError("execute_order")
    reg.available = []

    wf = TradingWorkflow(
        workflow_id="wf_exec_004",
        symbol="600519",
        market=MarketCode.CN,
        capability_registry=reg,
    )
    wf.start()

    result = wf._step_execute_order(
        MagicMock(data={
            "risk_check": {"risk_action": "allow", "trade_value": 50000},
            "generate_signal": {"signal_type": "buy", "indicators": {"close": 100}},
        }),
    )
    assert result["status"] == "simulated"
    assert "fallback_simulated" in result["execution_note"]


# ── End-to-End ────────────────────────────────────────────────────────────


def test_full_workflow_buy_signal() -> None:
    """Complete pipeline: bars → signal → risk → order."""
    bars = [{"close": 100.0 + i * 0.5} for i in range(30)]
    reg = _mock_registry(bars=bars, exec_result={"status": "executed", "order_id": "full_001"})

    wf = TradingWorkflow(
        workflow_id="wf_full_001",
        symbol="600519",
        market=MarketCode.CN,
        strategy_name="ma_cross",
        capability_registry=reg,
    )
    wf.start()

    status = wf.get_status()
    assert status["workflow_type"] == "trading"
    assert status["state"] in ("completed", "running")

    evidence = wf.get_evidence()
    assert len(evidence) >= 3  # at least 3 step results


def test_full_workflow_restricted_stock() -> None:
    """Restricted stock → signal generated → risk blocked → order skipped."""
    bars = [{"close": 50.0} for _ in range(10)]
    reg = _mock_registry(bars=bars)

    policy = TradingPolicy(restricted_stocks=("600519",))
    wf = TradingWorkflow(
        workflow_id="wf_full_002",
        symbol="600519",
        market=MarketCode.CN,
        trading_policy=policy,
        capability_registry=reg,
    )
    wf.start()

    # Step 1: signal generated
    signal_result = wf._step_generate_signal(MagicMock(data={}))
    assert signal_result["signal_type"] in ("buy", "sell", "hold")

    # Step 2: risk blocked
    risk_result = wf._step_risk_check(
        MagicMock(data={"generate_signal": {"signal_type": "buy", "confidence": 0.8}}),
    )
    assert risk_result["risk_action"] == "block"

    # Step 3: order skipped
    exec_result = wf._step_execute_order(
        MagicMock(data={
            "risk_check": risk_result,
            "generate_signal": signal_result,
        }),
    )
    assert exec_result["status"] == "skipped"


# ── Indicator Computation ─────────────────────────────────────────────────


def test_compute_indicators_empty() -> None:
    assert TradingWorkflow._compute_indicators(None) == {}
    assert TradingWorkflow._compute_indicators([]) == {}


def test_compute_indicators_with_bars() -> None:
    bars = [{"close": 100.0 + i} for i in range(25)]
    ind = TradingWorkflow._compute_indicators(bars)
    assert ind["close"] == 124.0
    assert ind["ma5"] > 0
    assert ind["ma20"] > 0
    assert 0 <= ind["rsi"] <= 100
    assert ind["period_high"] == 124.0
    assert ind["period_low"] == 100.0
