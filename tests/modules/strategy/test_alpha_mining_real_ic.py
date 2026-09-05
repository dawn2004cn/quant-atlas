"""Alpha mining IC decay / fitness / orthogonalize use real series."""

from __future__ import annotations

from app.modules.strategy.services.alpha_mining_service import AlphaFactor, AutoAlphaMiningService


def test_ic_decay_x0_matches_returns():
    svc = AutoAlphaMiningService()
    returns = [0.01 * ((-1) ** i) for i in range(80)]
    out = svc.compute_ic_decay("x0", returns, lookback_windows=[20, 40])
    assert out["ic_by_window"]["20"] > 0.99
    assert out["half_life"] is not None
    assert "error" not in out


def test_ic_decay_rejects_unknown_expression():
    svc = AutoAlphaMiningService()
    out = svc.compute_ic_decay("__import__('os')", [0.01] * 30, lookback_windows=[20])
    assert out["ic_by_window"] == {}
    assert out.get("error")


def test_fitness_from_ic_prefers_aligned_feature():
    svc = AutoAlphaMiningService()
    features = {"x0": [1, 2, 3, 4, 5, 6], "x1": [1, 1, 1, 1, 1, 1]}
    returns = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06]
    aligned = svc.fitness_from_ic("x0", features, returns)
    flat = svc.fitness_from_ic("x1", features, returns)
    assert aligned > flat
    assert aligned > 0.99


def test_dummy_fitness_without_market_data():
    svc = AutoAlphaMiningService()
    fn = svc.make_fitness()
    assert fn("add(x0,x1)") == len("add(x0,x1)") * 0.01 + 0.5


def test_orthogonalize_collinear_has_near_zero_residual():
    svc = AutoAlphaMiningService()
    factors = [
        AlphaFactor(factor_id="a", expression="x0"),
        AlphaFactor(factor_id="b", expression="add(x0,x0)"),
    ]
    features = {"x0": [1.0, 2.0, 3.0, 4.0, 5.0]}
    out = svc.orthogonalize(factors, features=features)
    assert out[1].orthogonalized
    assert getattr(out[1], "residual_norm") < 1e-9
