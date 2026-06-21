"""Prompt Evolution domain models."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PromptVariant:
    variant_id: str
    base_prompt: str
    mutated_prompt: str
    generation: int = 0
    parent_id: str | None = None
    mutation_type: str = "unknown"
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PromptEvaluation:
    evaluation_id: str
    variant_id: str
    accuracy: float = 0.0
    user_feedback_score: float = 0.0
    shadow_test_results: dict[str, Any] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=datetime.now)
