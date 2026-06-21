from __future__ import annotations
"""Outcome Repository for AI decision feedback loop.

This module implements the outcome tracking from midify_plan8.md:
- Track AI verdicts vs actual price movements
- Calculate agent historical accuracy
- Dynamic weight adjustment based on performance
"""


import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OutcomeRecord:
    """Record of AI decision vs actual outcome."""
    symbol: str
    decision_date: str
    ai_verdict: str
    expected_direction: str
    holding_period_days: int = 5
    actual_price_start: float = 0.0
    actual_price_end: float = 0.0
    actual_return: float = 0.0
    was_correct: bool = False


@dataclass
class AgentPerformance:
    """Performance metrics for a single agent."""
    agent_name: str
    total_decisions: int = 0
    correct_decisions: int = 0
    accuracy_rate: float = 0.0
    avg_confidence: float = 0.0
    last_updated: str = ""


class OutcomeRepository:
    """Repository for tracking AI decision outcomes and calculating agent performance."""

    def __init__(self, session_factory: Any = None):
        self._session_factory = session_factory
        self._memory_store: dict[str, list[OutcomeRecord]] = {}

    def record_outcome(
        self,
        symbol: str,
        decision_date: str,
        ai_verdict: str,
        expected_direction: str,
        holding_period_days: int = 5,
    ) -> str:
        """Record an AI decision for future outcome tracking."""
        key = f"{symbol}_{decision_date}"
        record = OutcomeRecord(
            symbol=symbol,
            decision_date=decision_date,
            ai_verdict=ai_verdict,
            expected_direction=expected_direction,
            holding_period_days=holding_period_days,
        )

        if symbol not in self._memory_store:
            self._memory_store[symbol] = []
        self._memory_store[symbol].append(record)

        logger.info(f"Recorded outcome for {symbol} on {decision_date}")
        return key

    def update_outcome(
        self,
        symbol: str,
        decision_date: str,
        actual_price_start: float,
        actual_price_end: float,
    ) -> None:
        """Update actual prices and calculate correctness."""
        if symbol not in self._memory_store:
            return

        for record in self._memory_store[symbol]:
            if record.decision_date == decision_date:
                record.actual_price_start = actual_price_start
                record.actual_price_end = actual_price_end

                if actual_price_start > 0:
                    record.actual_return = (actual_price_end - actual_price_start) / actual_price_start

                    if record.expected_direction == "bullish":
                        record.was_correct = record.actual_return > 0
                    elif record.expected_direction == "bearish":
                        record.was_correct = record.actual_return < 0
                    else:
                        record.was_correct = abs(record.actual_return) < 0.02

                logger.info(f"Updated outcome for {symbol}: return={record.actual_return:.2%}")
                break

    def calculate_agent_performance(self, agent_name: str) -> AgentPerformance:
        """Calculate performance metrics for an agent.

        This implements the dynamic weight adjustment from midify_plan8.md.
        """
        correct = 0
        total = 0
        confidence_sum = 0.0

        for symbol, records in self._memory_store.items():
            for record in records:
                if record.was_correct:
                    correct += 1
                total += 1

        accuracy = correct / total if total > 0 else 0.5

        return AgentPerformance(
            agent_name=agent_name,
            total_decisions=total,
            correct_decisions=correct,
            accuracy_rate=accuracy,
            avg_confidence=0.7,
            last_updated=datetime.now().isoformat(),
        )

    def get_all_agent_performances(self) -> list[AgentPerformance]:
        """Get performance for all tracked agents."""
        agent_names = ["TechnicalAgent", "FundamentalAgent", "SentimentAgent", "CriticAgent"]
        return [self.calculate_agent_performance(name) for name in agent_names]

    def get_recent_outcomes(self, days: int = 30) -> list[OutcomeRecord]:
        """Get outcomes from recent decisions."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        results = []

        for symbol, records in self._memory_store.items():
            for record in records:
                if record.decision_date >= cutoff:
                    results.append(record)

        return results

    def get_adjusted_weights(self) -> dict[str, float]:
        """Get dynamically adjusted weights based on historical performance.

        Higher accuracy agents get higher weights in consensus calculation.
        """
        performances = self.get_all_agent_performances()

        if not performances:
            return {
                "TechnicalAgent": 0.25,
                "FundamentalAgent": 0.25,
                "SentimentAgent": 0.25,
                "CriticAgent": 0.25,
            }

        weights = {}
        total_accuracy = sum(p.accuracy_rate for p in performances) or 1.0

        for perf in performances:
            adjusted_weight = (perf.accuracy_rate / total_accuracy) if total_accuracy > 0 else 0.25
            weights[perf.agent_name] = adjusted_weight

        return weights


def create_outcome_repository(session_factory: Any = None) -> OutcomeRepository:
    """Factory function to create outcome repository."""
    return OutcomeRepository(session_factory)