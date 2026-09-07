"""FactorPerformanceEngine scores real Rank IC, not a constant 1.0."""

from __future__ import annotations

from app.modules.system.services.alpha.factor_performance_engine import FactorPerformanceEngine


def test_unknown_factor_defaults_to_one():
    assert FactorPerformanceEngine().score_factor("missing") == 1.0


def test_record_aligned_factor_exceeds_immune_threshold():
    engine = FactorPerformanceEngine()
    engine.record("mom", [1, 2, 3, 4, 5], [0.1, 0.2, 0.3, 0.4, 0.5])
    assert engine.score_factor("mom") > 1.2
    assert engine.config_loader.get_config("factor_weights")["mom"] > 1.2
    diag = engine.diagnose("mom")
    assert diag is not None
    assert diag["rank_ic"] > 0.99


def test_config_override_without_observation():
    engine = FactorPerformanceEngine()
    engine.config_loader.get_config("factor_weights")["custom"] = 1.5
    assert engine.score_factor("custom") == 1.5
