from __future__ import annotations
"""Regime-aware portfolio risk budget manager.

This manager adjusts position limits based on detected market regime.
In volatile/bear regimes, it reduces exposure; in bull regimes, it increases.
"""


from dataclasses import dataclass
from enum import Enum
from app.core.logger import get_logger


logger = get_logger(__name__)


class RiskLevel(Enum):
    """Risk level classification."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass
class RiskBudget:
    """Risk budget for a strategy."""
    strategy_id: str
    position_limit: float
    stop_loss: float
    risk_level: RiskLevel


class RegimeAwarePortfolioManager:
    """Portfolio manager that adjusts risk based on market regime."""

    REGIME_CONFIGS = {
        "bull_strong": {
            "position_multiplier": 1.0,
            "stop_loss": 0.08,
            "risk_level": RiskLevel.AGGRESSIVE,
        },
        "bull_weak": {
            "position_multiplier": 0.8,
            "stop_loss": 0.06,
            "risk_level": RiskLevel.MODERATE,
        },
        "ranging": {
            "position_multiplier": 0.6,
            "stop_loss": 0.05,
            "risk_level": RiskLevel.MODERATE,
        },
        "volatile": {
            "position_multiplier": 0.4,
            "stop_loss": 0.03,
            "risk_level": RiskLevel.CONSERVATIVE,
        },
        "low_volatility": {
            "position_multiplier": 1.0,
            "stop_loss": 0.06,
            "risk_level": RiskLevel.MODERATE,
        },
        "bear_strong": {
            "position_multiplier": 0.3,
            "stop_loss": 0.02,
            "risk_level": RiskLevel.CONSERVATIVE,
        },
        "bear_weak": {
            "position_multiplier": 0.5,
            "stop_loss": 0.04,
            "risk_level": RiskLevel.CONSERVATIVE,
        },
    }

    def __init__(self, base_position_limit: float = 1.0):
        self._base_limit = base_position_limit
        self._current_budgets: dict[str, RiskBudget] = {}
        self._last_regime: str = "ranging"

    def calculate_budget(
        self,
        strategy_id: str,
        regime: str,
    ) -> RiskBudget:
        """Calculate risk budget for a strategy based on regime."""
        config = self.REGIME_CONFIGS.get(regime, self.REGIME_CONFIGS["ranging"])

        budget = RiskBudget(
            strategy_id=strategy_id,
            position_limit=self._base_limit * config["position_multiplier"],
            stop_loss=config["stop_loss"],
            risk_level=config["risk_level"],
        )

        self._current_budgets[strategy_id] = budget
        self._last_regime = regime

        logger.info(
            f"Risk budget for {strategy_id}: "
            f"pos_limit={budget.position_limit:.0%}, "
            f"stop_loss={budget.stop_loss:.0%}, "
            f"level={budget.risk_level.value}"
        )

        return budget

    def get_current_budget(self, strategy_id: str) -> RiskBudget | None:
        """Get current budget for a strategy."""
        return self._current_budgets.get(strategy_id)

    def get_total_exposure(self) -> float:
        """Get total portfolio exposure across all strategies."""
        return sum(b.position_limit for b in self._current_budgets.values())


_regime_manager: RegimeAwarePortfolioManager | None = None


def get_regime_portfolio_manager(
    base_position_limit: float = 1.0,
) -> RegimeAwarePortfolioManager:
    """Get the global regime-aware portfolio manager."""
    global _regime_manager
    if _regime_manager is None:
        _regime_manager = RegimeAwarePortfolioManager(base_position_limit)
    return _regime_manager
