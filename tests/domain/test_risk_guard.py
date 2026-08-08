"""SRS Risk Guard domain rules (REQ-SRS-01)."""

from app.domain.trading.risk_guard import RiskGuardDecision, evaluate_account_risk


def test_daily_drawdown_triggers_flatten():
    d = evaluate_account_risk(
        equity=95000.0,
        day_start_equity=100000.0,
        consecutive_stop_outs=0,
        max_daily_drawdown_pct=0.05,
        max_consecutive_stop_outs=3,
    )
    assert d.action == "flatten_all"
    assert d.block_new_orders is True
    assert isinstance(d, RiskGuardDecision)


def test_three_stop_outs_suspend_execution():
    d = evaluate_account_risk(
        equity=99000.0,
        day_start_equity=100000.0,
        consecutive_stop_outs=3,
        max_daily_drawdown_pct=0.05,
        max_consecutive_stop_outs=3,
    )
    assert d.action == "suspend_execution"
    assert d.block_new_orders is True


def test_within_limits_allows_trading():
    d = evaluate_account_risk(
        equity=99000.0,
        day_start_equity=100000.0,
        consecutive_stop_outs=1,
        max_daily_drawdown_pct=0.05,
        max_consecutive_stop_outs=3,
    )
    assert d.action == "allow"
    assert d.block_new_orders is False


def test_invalid_day_start_equity_suspends():
    d = evaluate_account_risk(
        equity=1000.0,
        day_start_equity=0.0,
        consecutive_stop_outs=0,
    )
    assert d.action == "suspend_execution"
    assert d.block_new_orders is True
