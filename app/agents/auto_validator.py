from __future__ import annotations

"""Auto-Validator - Automatic accuracy tracking for agent decisions.

This module implements the Closing the Feedback Loop from midify_plan10.md:
- AutoValidator: Automatically validates agent decisions
- Scheduled backtest to compare predictions with actual outcomes
- Real-time agent performance ranking

Usage:
    validator = AutoValidator()
    validator.validate_pending_decisions()
    rankings = validator.get_real_time_rankings()
"""


from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.core.logger import get_logger

from .agent_memory import get_agent_memory

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of validating a single decision."""
    memory_id: str
    symbol: str
    agent_name: str
    predicted_direction: str
    actual_direction: str
    accuracy_score: float
    holding_period_days: int
    return_pct: float
    validated_at: datetime


class AutoValidator:
    """Automatic validation of agent decisions.

    This runs periodically to:
    1. Find decisions that are old enough to validate
    2. Fetch actual price data
    3. Compare predictions with actual outcomes
    4. Update agent memory with accuracy scores
    """

    def __init__(
        self,
        market_data_provider: Any = None,
        holding_period_days: int = 5,
    ):
        self._market_provider = market_data_provider
        self._holding_period_days = holding_period_days

    async def validate_pending_decisions(
        self,
        days_threshold: int = 5,
    ) -> list[ValidationResult]:
        """Validate all pending decisions older than threshold days."""
        results = []

        from app.infrastructure.database.stock_cache_db import StockCache

        cache = StockCache.default()

        all_memories = get_agent_memory()

        pending_entries = [
            e for e in all_memories._memory
            if e.outcome == "pending"
        ]

        cutoff_date = datetime.now() - timedelta(days=days_threshold)

        for entry in pending_entries:
            if entry.timestamp < cutoff_date:
                result = await self._validate_single_decision(
                    entry,
                    cache,
                )
                if result:
                    results.append(result)

        return results

    async def _validate_single_decision(
        self,
        entry,
        cache,
    ) -> ValidationResult | None:
        """Validate a single decision."""
        try:
            symbol = entry.symbol

            start_price = self._get_price_on_date(cache, symbol, entry.timestamp)
            if not start_price:
                logger.warning(f"Could not find start price for {symbol}")
                return None

            end_price = self._get_current_price(cache, symbol)
            if not end_price:
                logger.warning(f"Could not find end price for {symbol}")
                return None

            actual_return = (end_price - start_price) / start_price

            predicted_direction = entry.content.lower()
            if "bullish" in predicted_direction or "buy" in predicted_direction:
                actual_direction = "bullish" if actual_return > 0 else "bearish"
            elif "bearish" in predicted_direction or "sell" in predicted_direction:
                actual_direction = "bearish" if actual_return < 0 else "bullish"
            else:
                actual_direction = "neutral"

            is_correct = predicted_direction == actual_direction
            accuracy_score = 1.0 if is_correct else (0.5 if abs(actual_return) < 0.02 else 0.0)

            from .agent_memory import get_agent_memory

            memory = get_agent_memory(symbol)
            memory.record_outcome(
                memory_id=entry.id,
                actual_outcome=actual_direction,
                accuracy_score=accuracy_score,
            )

            logger.info(f"Validated {entry.agent_name} on {symbol}: {accuracy_score:.2f}")

            return ValidationResult(
                memory_id=entry.id,
                symbol=symbol,
                agent_name=entry.agent_name,
                predicted_direction=entry.content,
                actual_direction=actual_direction,
                accuracy_score=accuracy_score,
                holding_period_days=self._holding_period_days,
                return_pct=actual_return * 100,
                validated_at=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Validation failed for {entry.id}: {e}")
            return None

    def _get_price_on_date(
        self,
        cache,
        symbol: str,
        date: datetime,
    ) -> float | None:
        """Get price on a specific date."""
        date_str = date.strftime("%Y-%m-%d")

        try:
            history = cache.get_stock_history(
                symbol,
                date_str,
                date_str,
            )
            if history and len(history) > 0:
                return float(history[0].get("close", 0))
        except Exception as e:
            logger.warning("auto_validator.py._get_price_on_date: %s", e)

        return None

    def _get_current_price(
        self,
        cache,
        symbol: str,
    ) -> float | None:
        """Get current price."""
        try:
            all_stocks = cache.get_all_stocks(max_age_minutes=5)
            for stock in all_stocks:
                if stock.get("code") == symbol:
                    return float(stock.get("price", 0))
        except Exception as e:
            logger.warning("auto_validator.py._get_current_price: %s", e)

        return None

    def get_real_time_rankings(self) -> list[dict[str, Any]]:
        """Get real-time agent performance rankings."""
        memory = get_agent_memory()

        agent_stats = {}

        for entry in memory._memory:
            if entry.outcome != "pending":
                if entry.agent_name not in agent_stats:
                    agent_stats[entry.agent_name] = {
                        "total": 0,
                        "correct": 0,
                        "avg_return": 0.0,
                        "recent": [],
                    }

                stats = agent_stats[entry.agent_name]
                stats["total"] += 1

                if entry.accuracy_score >= 0.5:
                    stats["correct"] += 1

                stats["recent"].append(entry.accuracy_score)

                if len(stats["recent"]) > 10:
                    stats["recent"] = stats["recent"][-10:]

        rankings = []
        for agent_name, stats in agent_stats.items():
            accuracy = stats["correct"] / stats["total"] if stats["total"] > 0 else 0.0
            recent_avg = sum(stats["recent"]) / len(stats["recent"]) if stats["recent"] else 0.0

            rankings.append({
                "agent_name": agent_name,
                "total_decisions": stats["total"],
                "accuracy": accuracy,
                "recent_performance": recent_avg,
                "trend": "improving" if recent_avg > accuracy else "declining",
            })

        rankings.sort(key=lambda x: x["accuracy"], reverse=True)

        for i, r in enumerate(rankings):
            r["rank"] = i + 1

        return rankings


def create_validator(market_provider: Any = None) -> AutoValidator:
    """Factory to create auto validator."""
    return AutoValidator(market_provider)
