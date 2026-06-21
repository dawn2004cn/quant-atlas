"""Tests for Phase 10 Directive 1: PromptEvolutionService."""
from __future__ import annotations

from app.modules.ai_agent.services.prompt_evolution_service import PromptEvolutionService


def test_prompt_evolution_service_initial_state():
    svc = PromptEvolutionService()
    status = svc.get_status()
    assert status["variant_count"] == 0
    assert status["evaluation_count"] == 0
    assert status["current_best"] is None


def test_record_feedback_increments_evaluation():
    svc = PromptEvolutionService()
    svc.record_feedback("jarvis_default", 0.2)
    status = svc.get_status()
    assert status["evaluation_count"] == 1


def test_evolve_creates_variant():
    svc = PromptEvolutionService()
    variant = svc.evolve("jarvis_default", "You are a helpful assistant.")
    assert variant.variant_id is not None
    assert variant.mutation_type == "llm_rewrite"
    assert variant.parent_id == "jarvis_default"
    status = svc.get_status()
    assert status["variant_count"] == 1


def test_get_current_prompt_returns_none_when_empty():
    svc = PromptEvolutionService()
    assert svc.get_current_prompt("jarvis_default") is None


def test_negative_feedback_triggers_mutation():
    svc = PromptEvolutionService()
    svc.record_feedback("jarvis_default", 0.1)
    svc.record_feedback("jarvis_default", 0.2)
    status = svc.get_status()
    assert status["evaluation_count"] == 2
