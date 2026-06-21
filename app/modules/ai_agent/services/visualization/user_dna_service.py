from __future__ import annotations

import random
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class UserDNAService:
    """Aggregate user behaviors into DNA metrics for visualization."""

    @staticmethod
    def generate_dna(user_id: str | int, history_dataset: list[dict[str, Any]]) -> dict[str, float]:
        """Analyze historical decisions and output behavioral coefficients."""
        logger.info("Generating DNA fingerprint for user %s", user_id)
        if not history_dataset:
            return {"winning_buy_ratio": 0.5, "volatility_tolerance": 1.0, "momentum_bias": 0.0}

        total_trades = len(history_dataset)
        winning_trades = sum(1 for d in history_dataset if d.get("outcome", 0) > 0.1)

        avg_win = (winning_trades / total_trades) * 1.2 + random.uniform(-0.1, 0.1)

        min_risk = min([d["risk"] for d in history_dataset if "risk" in d] or [0.5])
        vola_tol = 1.0 / (1.0 + min_risk) * random.uniform(0.9, 1.1)

        mom_bias = (
            (total_trades / max(50, total_trades))
            * (winning_trades / total_trades)
            * random.uniform(0.8, 1.2)
        )

        return {
            "winning_buy_ratio": round(avg_win, 3),
            "volatility_tolerance": round(vola_tol, 3),
            "momentum_bias": round(mom_bias, 3),
        }

    @staticmethod
    def get_intervention_overlay_data(
        proposed_action: str,
        current_dna_metrics: dict[str, float],
    ) -> dict[str, Any]:
        """Predictive simulation overlay for UI intervention paths."""
        results: dict[str, float] = {}
        base_risk = 0.6 + (current_dna_metrics.get("volatility_tolerance", 1.0) * 0.2)
        _ = base_risk

        path_a_prob = max(
            0.5,
            current_dna_metrics["momentum_bias"] * 0.8 + random.uniform(0.1, 0.3),
        )
        results["Optimal Path (DNA Alignment)"] = round(min(1.0, path_a_prob), 2)

        path_b_prob = max(
            0.2,
            0.4 - current_dna_metrics["momentum_bias"] * 0.1 + random.uniform(-0.1, 0.1),
        )
        results["Conservative Path (Mitigating)"] = round(min(1.0, path_b_prob), 2)

        if (
            current_dna_metrics.get("volatility_tolerance", 1.0) <= 0.6
            and proposed_action in ("ALL_CAPITALIZE", "HIGH_LEVERAGE")
        ):
            results["High Risk Warning"] = 0.05

        return results
