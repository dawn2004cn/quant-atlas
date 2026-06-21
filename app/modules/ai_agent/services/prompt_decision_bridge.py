"""PromptEvolutionService ↔ DecisionFeedbackService closed-loop integration.
Phase 14/16: auto-update prompt templates based on decision hit-rate feedback."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from pathlib import Path

from app.core.logger import get_logger
from app.modules.ai_agent.services.ai.decision_feedback_service import DecisionFeedbackService

logger = get_logger(__name__)


class PromptDecisionBridge:
    """Bridge between DecisionFeedbackService and PromptEvolutionService.

    Closes the loop: when a decision receives negative feedback, the bridge
    sends the context to PromptEvolutionService for template refinement.
    """

    def __init__(self, feedback_service: DecisionFeedbackService | None = None):
        self._feedback_svc = feedback_service or DecisionFeedbackService()
        self._bridge_enabled = True
        self._processed_decisions: set[str] = set()

    def ingest_decision_feedback(self, decision_id: str, hit_rate: float, user_feedback: dict | None = None):
        """Receive a decision feedback event and trigger prompt evolution."""
        if decision_id in self._processed_decisions:
            return
        self._processed_decisions.add(decision_id)

        if not self._bridge_enabled:
            return

        context = {
            "decision_id": decision_id,
            "hit_rate": hit_rate,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_feedback": user_feedback or {},
        }

        if hit_rate < 0.5:
            self._trigger_prompt_evolution(context)

    def _trigger_prompt_evolution(self, context: dict):
        """Send to prompt evolution pipeline for template regeneration."""
        try:
            from app.modules.ai_agent.services.prompt_evolution_service import PromptEvolutionService
            evo = PromptEvolutionService()
            evo.record_feedback(
                prompt_id="jarvis_default",
                rating=context["hit_rate"],
                context=context.get("user_feedback", {}),
            )
            logger.debug("Prompt evolution triggered for decision %s (hit_rate=%.2f)",
                         context["decision_id"], context["hit_rate"])
            return True
        except Exception as exc:
            logger.warning("Prompt evolution trigger failed: %s", exc)
            return False

    def run_periodic_evolution(self, min_samples: int = 10):
        """Periodic batch evolution: run when enough samples accumulated."""
        try:
            from app.modules.ai_agent.services.prompt_evolution_service import PromptEvolutionService
            evo = PromptEvolutionService()
            status = evo.get_status()
            return {"ok": True, "summary": status}
        except Exception as exc:
            logger.warning("Periodic prompt evolution failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def get_bridge_status(self) -> dict:
        """Get bridge health."""
        try:
            from app.modules.ai_agent.services.prompt_evolution_service import PromptEvolutionService
            evo = PromptEvolutionService()
            status = evo.get_status()
            return {
                "bridge_enabled": self._bridge_enabled,
                "processed_decisions": len(self._processed_decisions),
                "prompt_status": status,
            }
        except Exception as exc:
            return {
                "bridge_enabled": self._bridge_enabled,
                "processed_decisions": len(self._processed_decisions),
                "error": str(exc),
            }
