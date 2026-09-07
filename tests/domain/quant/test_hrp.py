"""Lopez de Prado Hierarchical Risk Parity (PyPortfolioOpt-style)."""

from __future__ import annotations

import math

from app.domain.quant.hrp import hrp_weights


def test_hrp_equal_for_identical_uncorrelated_series():
    returns = {
        "a": [0.01, -0.01, 0.02, -0.02, 0.01, 0.00, -0.01, 0.02],
        "b": [0.02, -0.02, 0.01, -0.01, 0.00, 0.01, -0.02, 0.01],
        "c": [-0.01, 0.01, -0.02, 0.02, 0.01, -0.01, 0.00, 0.02],
    }
    w = hrp_weights(returns)
    assert set(w) == {"a", "b", "c"}
    assert math.isclose(sum(w.values()), 1.0, rel_tol=1e-9)
    assert all(v > 0 for v in w.values())


def test_hrp_downweights_high_volatility_asset():
    calm = [0.01, -0.01, 0.01, -0.01, 0.01, -0.01, 0.01, -0.01]
    wild = [0.08, -0.08, 0.09, -0.09, 0.07, -0.07, 0.10, -0.10]
    w = hrp_weights({"calm": calm, "wild": wild})
    assert w["calm"] > w["wild"]
    assert math.isclose(sum(w.values()), 1.0, rel_tol=1e-9)


def test_hrp_empty_returns_empty_weights():
    assert hrp_weights({}) == {}


def test_hrp_single_asset_is_one():
    assert hrp_weights({"only": [0.01, 0.02, -0.01]}) == {"only": 1.0}
