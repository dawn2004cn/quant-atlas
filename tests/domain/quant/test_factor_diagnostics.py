"""Alphalens/Qlib-style factor IC, ICIR, and quantile returns."""

from __future__ import annotations

from app.domain.quant.factor_diagnostics import diagnose_factor


def test_perfect_rank_alignment_gives_ic_near_one():
    factor = [1.0, 2.0, 3.0, 4.0, 5.0]
    fwd = [0.01, 0.02, 0.03, 0.04, 0.05]
    out = diagnose_factor(factor, fwd)
    assert out["rank_ic"] > 0.99
    assert out["ic"] > 0.99
    assert out["sample_size"] == 5


def test_inverted_factor_gives_negative_ic():
    factor = [5.0, 4.0, 3.0, 2.0, 1.0]
    fwd = [0.01, 0.02, 0.03, 0.04, 0.05]
    out = diagnose_factor(factor, fwd)
    assert out["rank_ic"] < -0.99


def test_quantile_returns_are_monotonic_for_aligned_factor():
    factor = list(range(10))
    fwd = [x * 0.01 for x in factor]
    out = diagnose_factor(factor, fwd, n_quantiles=5)
    q = out["quantile_returns"]
    assert len(q) == 5
    assert q[-1] > q[0]
    assert out["long_short"] == q[-1] - q[0]


def test_panel_icir_is_mean_ic_over_std():
    # 4 dates × 5 names, factor perfectly ranks next-day return each date
    factor = [
        [1, 2, 3, 4, 5],
        [1, 2, 3, 4, 5],
        [1, 2, 3, 4, 5],
        [1, 2, 3, 4, 5],
    ]
    fwd = [
        [0.01, 0.02, 0.03, 0.04, 0.05],
        [0.02, 0.03, 0.04, 0.05, 0.06],
        [0.00, 0.01, 0.02, 0.03, 0.04],
        [0.03, 0.04, 0.05, 0.06, 0.07],
    ]
    out = diagnose_factor(factor, fwd)
    assert out["rank_ic"] > 0.99
    assert out["icir"] != 0.0
    assert out["n_periods"] == 4


def test_mismatched_or_short_input_is_empty():
    out = diagnose_factor([1.0], [0.1])
    assert out["rank_ic"] == 0.0
    assert out["sample_size"] == 0
