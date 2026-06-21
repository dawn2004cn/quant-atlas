"""Portfolio detail risk metrics."""

from __future__ import annotations

from app.presentation.api.v1.portfolio.detail_routes import _compute_portfolio_risk


def test_compute_portfolio_risk_from_holdings():
    holdings = [
        {"value": 60000, "pnl": 5.0},
        {"value": 40000, "pnl": -3.0},
    ]
    risk = _compute_portfolio_risk(holdings)
    assert "sharpe" in risk
    assert risk["max_drawdown"] == -3.0
    assert risk["beta"] is None
    assert risk["volatility"] >= 0
