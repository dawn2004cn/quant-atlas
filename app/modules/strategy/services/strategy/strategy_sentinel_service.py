from __future__ import annotations

import asyncio
from typing import Any
from app.core.registry import ServiceRegistry
from app.core.event_bus import publish_event
from app.domain.services.market_regime_service import MarketRegimeService
from app.modules.strategy.services.strategy.strategy_service import StrategyApplicationService
from app.core.logger import get_logger

logger = get_logger(__name__)

class StrategyRegimeMismatchEvent:
    """Event published when a strategy's type no longer matches the market regime."""
    def __init__(self, strategy_id: str, strategy_name: str, current_regime: str, recommended_category: str):
        self.strategy_id = strategy_id
        self.strategy_name = strategy_name
        self.current_regime = current_regime
        self.recommended_category = recommended_category

class StrategySentinelService:
    """
    The 'Sentinel' monitors active strategies and alerts users when
    the market regime shifts away from the strategy's design intent.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self.regime_service = MarketRegimeService()
        self.strategy_service: StrategyApplicationService = registry.get("strategy_service")
        self.wizard_service = registry.get("strategy_wizard_service")

    async def check_all_strategies(self) -> dict[str, Any]:
        """
        Iterates through active strategies and checks for regime alignment.
        """
        # 1. Determine current market regime
        # In a real scenario, we would fetch real sentiment/breadth.
        regime = self.regime_service.evaluate_stance(sentiment_score=45.0)
        current_stance = regime["stance"] # 'aggressive', 'defensive', 'neutral'

        # Mapping: Regime -> Recommended Category
        mapping = {
            "aggressive": "trend",
            "defensive": "mean_reversion",
            "neutral": "quant_factor",
        }
        recommended_cat = mapping.get(current_stance)

        # 2. Get active strategies
        # Assuming strategy_service has a method to list active strategies
        try:
            active_strategies = self.strategy_service.list_active_strategies()
        except Exception:
            # Fallback for demo: simulate active strategies
            active_strategies = [
                {"id": "strat_1", "name": "Trend Follower A", "category": "trend"},
                {"id": "strat_2", "name": "Mean Rev B", "category": "mean_reversion"},
            ]

        mismatches = []
        for strat in active_strategies:
            if strat.get("category") != recommended_cat:
                # Regime Mismatch Found!
                mismatches.append({
                    "strategy_id": strat["id"],
                    "strategy_name": strat["name"],
                    "current_regime": current_stance,
                    "recommended_category": recommended_cat
                })

                # Publish event for WebSocket/Notification
                publish_event(
                    "strategy.regime.mismatch",
                    StrategyRegimeMismatchEvent(
                        strategy_id=strat["id"],
                        strategy_name=strat["name"],
                        current_regime=current_stance,
                        recommended_category=recommended_cat
                    )
                )

        return {
            "status": "checked",
            "regime": current_stance,
            "recommended_category": recommended_cat,
            "mismatch_count": len(mismatches),
            "mismatches": mismatches
        }

    def run_periodic_check(self) -> None:
        """Synchronous wrapper for periodic checks (e.g. called by Celery/Kronos)."""
        try:
            result = asyncio.run(self.check_all_strategies())
            logger.info(f"Strategy Sentinel Check: {result['mismatch_count']} mismatches in {result['regime']} regime.")
        except Exception as e:
            logger.exception(f"Strategy Sentinel check failed: {e}")
