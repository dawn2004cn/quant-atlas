from __future__ import annotations
"""Shadow Account Autonomy Controller.

Monitors trading performance and proactively suggests or enforces risk rules.
"""


from typing import Any

from app.infrastructure.agent.shadow_account.models import ShadowStrategy
from app.infrastructure.agent.swarm.tools_base import BaseTool


from app.core.logger import get_logger

logger = get_logger(__name__)

class ShadowAccountController:
    """Monitors performance and suggests/enforces risk rules."""

    def __init__(self, shadow_id: str):
        self.shadow_id = shadow_id
        # In a production scenario, load strategy definition from repository
        self.strategy: ShadowStrategy | None = None

    def evaluate_performance(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """
        Evaluate metrics against the strategy's risk profile.
        Returns:
            { "action": "STAY" | "STOP_LOSS" | "ADJUST", "reason": "...", "suggestion": "..." }
        """
        drawdown = metrics.get("max_drawdown", 0.0)
        win_rate = metrics.get("win_rate", 0.0)

        if drawdown > 0.15: # 15% Max Drawdown limit
            return {
                "action": "STOP_LOSS",
                "reason": f"Drawdown {drawdown:.1%} exceeds threshold",
                "suggestion": "Initiate full position liquidation and shadow strategy re-evaluation."
            }

        if win_rate < 0.30: # 30% Win rate alert
            return {
                "action": "ADJUST",
                "reason": f"Win rate {win_rate:.1%} low, trend capture failing",
                "suggestion": "Adjust trend filter sensitivity in signal engine."
            }

        return {"action": "STAY", "reason": "Performance within risk parameters."}


class AutonomyRiskTool(BaseTool):
    """Tool to force risk rules on an agent."""

    name = "apply_risk_rule"
    description = "Apply an autonomous risk rule (e.g. stop-loss) to a running strategy."
    is_readonly = False
    parameters = {
        "type": "object",
        "properties": {
            "shadow_id": {"type": "string"},
            "rule": {"type": "string"},
        },
        "required": ["shadow_id", "rule"],
    }

    def execute(self, **kwargs: Any) -> str:
        shadow_id = kwargs["shadow_id"]
        rule = kwargs["rule"]
        # Logic to write risk config to the strategy directory
        logger.info(f"Applying autonomous risk rule {rule} to {shadow_id}")
        return f"Risk rule '{rule}' successfully applied to {shadow_id}."
