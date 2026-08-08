from __future__ import annotations
"""QualityChecker rule engine for market data validation.

This module defines modular rules to intercept anomalous market data
before it reaches agents or persistence layers.
"""


from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class QualityResult:
    is_valid: bool
    reason: str
    severity: str = "INFO"  # INFO, WARN, ERROR


class QualityRule:
    """Base class for market data validation rules."""

    def check(self, data: Any) -> QualityResult:
        raise NotImplementedError


class TradingHaltRule(QualityRule):
    """Detect if the instrument is halted."""

    def check(self, data: Any) -> QualityResult:
        # Check for halt status in data, e.g., 'is_suspended'
        if data.get("is_suspended"):
            return QualityResult(False, "Instrument is suspended", "ERROR")
        return QualityResult(True, "OK")


class VolatilityRule(QualityRule):
    """Detect abnormal volatility."""

    def __init__(self, threshold_pct: float = 0.20):
        self.threshold = threshold_pct

    def check(self, data: Any) -> QualityResult:
        pct_change = abs(data.get("change_pct", 0.0) / 100.0)
        if pct_change > self.threshold:
            return QualityResult(False, f"Volatility exceeds {self.threshold*100}%", "WARN")
        return QualityResult(True, "OK")


class QualityChecker:
    """Orchestrator for multiple quality rules."""

    def __init__(self, rules: List[QualityRule] | None = None):
        self.rules = rules or [
            TradingHaltRule(),
            VolatilityRule()
        ]

    def validate(self, data: Any) -> List[QualityResult]:
        results = []
        for rule in self.rules:
            res = rule.check(data)
            if not res.is_valid:
                results.append(res)
        return results
