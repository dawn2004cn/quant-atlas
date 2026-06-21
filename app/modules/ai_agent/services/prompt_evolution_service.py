"""Prompt Evolution Service — feedback-driven prompt mutation and selection."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.domain.prompt_evolution import PromptEvaluation, PromptVariant

logger = get_logger(__name__)

_MUTATION_STRATEGIES = [
    "risk_first",
    "data_first",
    "conservative",
    "structured",
    "verbose",
    "concise",
]


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


class PromptEvolutionService:
    """Prompt evolution with persistence and adaptive mutation.

    - Persists variants and evaluations to JSONL.
    - Selects mutation strategy based on feedback patterns.
    - Can inject current best prompt into agent adapter via ``get_current_prompt()``.
    """

    def __init__(
        self,
        feedback_service: Any | None = None,
        knowledge_service: Any | None = None,
        store_path: Path | str | None = None,
    ) -> None:
        self._feedback = feedback_service
        self._knowledge = knowledge_service
        self._variants: dict[str, PromptVariant] = {}
        self._evaluations: dict[str, PromptEvaluation] = {}
        self._current_best: str | None = None

        if store_path is None:
            store_path = Path(__file__).resolve().parents[4] / "instance" / "prompt_evolution.jsonl"
        self._store_path = Path(store_path)
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_persisted()

    def get_current_prompt(self, prompt_id: str = "jarvis_default") -> str | None:
        variant = self._variants.get(self._current_best or prompt_id)
        return variant.mutated_prompt if variant else None

    def get_current_prompt_snapshot(self, prompt_id: str = "jarvis_default") -> dict[str, Any]:
        variant = self._variants.get(self._current_best or prompt_id)
        if variant is None:
            prompt = prompt_id
            return {
                "prompt_id": prompt_id,
                "prompt_version": prompt_id,
                "prompt_hash": prompt_hash(prompt),
                "prompt": prompt,
            }
        return {
            "prompt_id": variant.variant_id,
            "prompt_version": variant.variant_id,
            "prompt_hash": prompt_hash(variant.mutated_prompt),
            "prompt": variant.mutated_prompt,
        }

    def rollback(self, prompt_id: str) -> bool:
        if prompt_id not in self._variants:
            return False
        self._current_best = prompt_id
        return True

    def record_feedback(self, prompt_id: str, rating: float, context: dict[str, Any] | None = None) -> None:
        if not self._current_best:
            self.evolve(prompt_id, "默认：基于证据和风险约束生成回答。")
        score = max(0.0, min(1.0, float(rating)))
        evaluation = PromptEvaluation(
            evaluation_id=f"eval-{uuid.uuid4().hex[:8]}",
            variant_id=prompt_id,
            user_feedback_score=score,
            shadow_test_results=context or {},
        )
        self._evaluations[evaluation.evaluation_id] = evaluation
        self._persist_evaluation(evaluation)

        if score < 0.3 and self._current_best:
            self.evolve(self._current_best, self._current_best)
        elif score >= 0.7:
            self._current_best = prompt_id

    def evolve(self, prompt_id: str, base_prompt: str | None = None) -> PromptVariant:
        base = base_prompt or self._current_best or prompt_id
        strategy = self._select_strategy(prompt_id)
        variant_id = f"var-{uuid.uuid4().hex[:8]}"
        mutated = self._mutate_prompt(base, strategy)
        variant = PromptVariant(
            variant_id=variant_id,
            base_prompt=base,
            mutated_prompt=mutated,
            parent_id=prompt_id,
            generation=self._next_generation(prompt_id),
            mutation_type=strategy,
            metadata={"strategy": strategy, "source": "auto_evolution"},
        )
        self._variants[variant_id] = variant
        self._current_best = variant_id
        self._persist_variant(variant)
        logger.info("Evolved prompt %s -> %s (strategy=%s)", prompt_id, variant_id, strategy)
        return variant

    def get_status(self) -> dict[str, Any]:
        return {
            "variant_count": len(self._variants),
            "evaluation_count": len(self._evaluations),
            "current_best": self._current_best,
        }

    def list_variants(self, *, limit: int = 20) -> list[dict[str, Any]]:
        rows = sorted(self._variants.values(), key=lambda item: item.created_at, reverse=True)
        return [self._variant_to_dict(v) for v in rows[:limit]]

    def list_evaluations(self, *, limit: int = 20) -> list[dict[str, Any]]:
        rows = sorted(self._evaluations.values(), key=lambda item: item.evaluated_at, reverse=True)
        return [
            {
                "evaluation_id": e.evaluation_id,
                "variant_id": e.variant_id,
                "user_feedback_score": e.user_feedback_score,
                "evaluated_at": e.evaluated_at.isoformat(),
            }
            for e in rows[:limit]
        ]

    def _select_strategy(self, prompt_id: str) -> str:
        """Select mutation strategy based on recent feedback scores."""
        recent = [
            e for e in self._evaluations.values()
            if e.variant_id == prompt_id
        ][-5:]
        if not recent:
            return _MUTATION_STRATEGIES[len(self._variants) % len(_MUTATION_STRATEGIES)]
        avg = sum(e.user_feedback_score for e in recent) / len(recent)
        if avg < 0.2:
            return "conservative"
        if avg < 0.4:
            return "structured"
        return _MUTATION_STRATEGIES[hash(prompt_id + str(len(self._variants))) % len(_MUTATION_STRATEGIES)]

    def _next_generation(self, prompt_id: str) -> int:
        existing = [v for v in self._variants.values() if v.parent_id == prompt_id]
        return max((v.generation for v in existing), default=0) + 1

    def _mutate_prompt(self, prompt: str, strategy: str) -> str:
        hints = {
            "risk_first": "\n\n[系统约束] 请先确认用户风险承受等级再给出建议。优先说明下行风险和最大可能亏损。",
            "data_first": "\n\n[系统约束] 所有结论必须附带数据支撑。引用数据时标注来源与时间戳。缺少数据时明确声明。",
            "conservative": "\n\n[系统约束] 避免过度乐观表述。包含明确的风险警告。如用户未授权，不要建议实盘操作。",
            "structured": "\n\n[系统约束] 按以下结构输出：1. 核心观点 2. 数据支撑 3. 风险因素 4. 操作建议。",
            "verbose": "\n\n[系统约束] 提供详细分析过程，包括多空双方论据。不要省略推理步骤。",
            "concise": "\n\n[系统约束] 保持回答简洁，优先给出结论。若无必要不展开背景说明。",
        }
        return prompt + hints.get(strategy, hints["conservative"])

    def _variant_to_dict(self, variant: PromptVariant) -> dict[str, Any]:
        return {
            "variant_id": variant.variant_id,
            "base_prompt": variant.base_prompt,
            "mutated_prompt": variant.mutated_prompt,
            "generation": variant.generation,
            "parent_id": variant.parent_id,
            "mutation_type": variant.mutation_type,
            "created_at": variant.created_at.isoformat(),
            "metadata": variant.metadata,
        }

    def _persist_variant(self, variant: PromptVariant) -> None:
        entry = {
            "type": "variant",
            "variant_id": variant.variant_id,
            "base_prompt": variant.base_prompt,
            "mutated_prompt": variant.mutated_prompt,
            "generation": variant.generation,
            "parent_id": variant.parent_id,
            "mutation_type": variant.mutation_type,
            "created_at": variant.created_at.isoformat(),
            "metadata": variant.metadata,
        }
        with open(self._store_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _persist_evaluation(self, evaluation: PromptEvaluation) -> None:
        entry = {
            "type": "evaluation",
            "evaluation_id": evaluation.evaluation_id,
            "variant_id": evaluation.variant_id,
            "user_feedback_score": evaluation.user_feedback_score,
            "shadow_test_results": evaluation.shadow_test_results,
            "evaluated_at": evaluation.evaluated_at.isoformat(),
        }
        with open(self._store_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _load_persisted(self) -> None:
        if not self._store_path.exists():
            return
        with open(self._store_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue
                if data.get("type") == "variant":
                    variant = PromptVariant(
                        variant_id=data["variant_id"],
                        base_prompt=data["base_prompt"],
                        mutated_prompt=data["mutated_prompt"],
                        generation=data.get("generation", 0),
                        parent_id=data.get("parent_id"),
                        mutation_type=data.get("mutation_type", "unknown"),
                        metadata=data.get("metadata", {}),
                    )
                    self._variants[variant.variant_id] = variant
                elif data.get("type") == "evaluation":
                    evaluation = PromptEvaluation(
                        evaluation_id=data["evaluation_id"],
                        variant_id=data["variant_id"],
                        user_feedback_score=data.get("user_feedback_score", 0.0),
                        shadow_test_results=data.get("shadow_test_results", {}),
                    )
                    self._evaluations[evaluation.evaluation_id] = evaluation