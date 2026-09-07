"""PortfolioOptimizer must expose HRP alongside MVO / risk budget."""

from __future__ import annotations

from app.domain.allocation.portfolio_optimizer import PortfolioOptimizer


def test_optimize_with_correlation_hrp_sums_to_one():
    returns = {
        "a": [0.01, -0.01, 0.02, -0.02, 0.01, 0.00],
        "b": [0.03, -0.03, 0.01, -0.01, 0.02, -0.01],
        "c": [-0.01, 0.02, -0.01, 0.01, 0.00, 0.01],
    }
    expected = {"a": 0.08, "b": 0.10, "c": 0.06}
    opt = PortfolioOptimizer()
    weights = opt.optimize_with_correlation(returns, expected, method="hrp")
    assert set(weights) == {"a", "b", "c"}
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    assert all(v > 0 for v in weights.values())
