"""Tests for Phase 9 Directive 2: Alpha metadata standard."""
from __future__ import annotations

from app.domain.alpha.alpha_metadata_standard import (
    AlphaNote,
    FactorCategory,
    FactorComposition,
    FactorExpression,
    CompositionOp,
)


def test_factor_expression_to_dict():
    expr = FactorExpression(
        raw_expression="Rank(ROC(close, 20)) * Volume",
        category=FactorCategory.MOMENTUM,
        source="rd_agent",
    )
    d = expr.to_dict()
    assert d["category"] == "momentum"
    assert d["source"] == "rd_agent"
    assert "Rank" in d["raw_expression"]


def test_alpha_note_to_evidence_note():
    expr = FactorExpression(raw_expression="Mean(close, 5) / Mean(close, 20)")
    note = AlphaNote(
        note_id="alpha-001",
        symbol="000001",
        title="MA Golden Cross",
        expression=expr,
        ic=0.12,
        sharpe=2.1,
        tags=["momentum", "ma"],
    )
    evidence = note.to_evidence_note()
    assert evidence["agent_role"] == "alpha_lab"
    assert evidence["strength"] == "strong"
    assert evidence["payload"]["ic"] == 0.12
    assert evidence["payload"]["expression"]["category"] == "technical"
    assert evidence["payload"]["tags"] == ["momentum", "ma"]


def test_factor_composition():
    comp = FactorComposition(
        expression_a="Rank(ROC(close, 20))",
        expression_b="Volume",
        operation=CompositionOp.MULTIPLY,
    )
    assert "Compose" in comp.combined_expression()
    assert "multiply" in comp.combined_expression()


def test_alpha_note_without_expression():
    note = AlphaNote(note_id="alpha-002", title="Manual Factor", ic=0.03)
    evidence = note.to_evidence_note()
    assert evidence["strength"] == "medium"
    assert evidence["payload"]["expression"] is None
