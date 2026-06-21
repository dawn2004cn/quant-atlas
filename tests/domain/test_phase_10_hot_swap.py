"""Tests for Phase 10.2 Shadow Factor Pool + AlphaHotSwap."""
from __future__ import annotations

from app.domain.alpha.shadow_factor_pool import (
    AlphaHotSwapService,
    CandidateFactor,
    HotSwapDecision,
    ShadowFactorPool,
)


def test_shadow_pool_standby_selection():
    pool = ShadowFactorPool()
    pool.add_candidate(CandidateFactor(candidate_id="c1", expression="Rank(close)", category="momentum", complementarity_score=0.8, status="standby"))
    pool.add_candidate(CandidateFactor(candidate_id="c2", expression="Volume", category="volatility", complementarity_score=0.9, status="standby"))
    standby = pool.get_standby(decayed_category="momentum")
    assert standby is not None
    assert standby.candidate_id == "c2"


def test_hot_swap_triggers_only_above_threshold():
    svc = AlphaHotSwapService()
    decision = svc.evaluate_hot_swap("f1", decay_rate=0.2, category="momentum")
    assert decision is None
    decision = svc.evaluate_hot_swap("f2", decay_rate=0.4, category="momentum")
    assert decision is None  # pool empty, no standby candidate

def test_hot_swap_records_decision():
    pool = ShadowFactorPool()
    pool.add_candidate(CandidateFactor(candidate_id="c3", expression="ROC(close,20)", category="reversal", complementarity_score=0.7, status="standby"))
    svc = AlphaHotSwapService(pool=pool)
    decision = svc.evaluate_hot_swap("f3", decay_rate=0.36, category="momentum")
    assert decision is not None
    assert decision.replacement_candidate_id == "c3"
    recent = pool.recent_decisions(limit=1)
    assert len(recent) == 1
    assert recent[0].decision_id == decision.decision_id
