"""Tests for Phase 9 Directive 1: IntentDecomposer."""
from __future__ import annotations

from app.modules.ai_agent.services.intention.intent_decomposer import IntentDecomposer
from app.domain.intent_decomposer import ExecutionPlan, StepType


def test_review_loss_intent_decomposes_correctly():
    decomposer = IntentDecomposer()
    plan = decomposer.decompose("帮我复盘上周亏损最严重的策略并提出改进建议", symbol="000001")
    assert isinstance(plan, ExecutionPlan)
    assert plan.intent == "复盘亏损策略"
    assert plan.symbol == "000001"
    assert len(plan.steps) == 5
    types = [s.step_type for s in plan.steps]
    assert types == [
        StepType.FETCH_DATA,
        StepType.CALCULATE,
        StepType.ARBITER_REVIEW,
        StepType.OPTIMIZE,
        StepType.NOTIFY,
    ]


def test_factor_mining_intent():
    decomposer = IntentDecomposer()
    plan = decomposer.decompose("挖掘新的 alpha 因子", symbol="600519")
    assert plan.intent == "因子挖掘"
    assert len(plan.steps) == 4


def test_default_fallback():
    decomposer = IntentDecomposer()
    plan = decomposer.decompose("随便看看", symbol="")
    assert plan.intent == "默认"
    assert len(plan.steps) == 3
