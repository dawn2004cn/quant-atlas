from __future__ import annotations
"""Negative constraints library for RD-Agent.

This implements the "Guardrails" from quant_plan.md:
- Hard constraints that must not be violated
- Prevents "toxic factors" from entering production
- Auto-circuit-breaker if连续 failures occur
"""


import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class ConstraintType(Enum):
    """Type of constraint."""
    FORBIDDEN_FUNCTION = "forbidden_function"
    TRADING_RULE = "trading_rule"
    RISK_LIMIT = "risk_limit"
    DATA_QUALITY = "data_quality"


class ViolationSeverity(Enum):
    """Severity of constraint violation."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ConstraintViolation:
    """A constraint violation."""
    constraint_type: str
    description: str
    severity: ViolationSeverity
    suggested_fix: str | None = None


@dataclass
class ConstraintResult:
    """Result of constraint checking."""
    is_allowed: bool
    violations: list[ConstraintViolation]
    warnings: list[str]


class NegativeConstraints:
    """Library of negative constraints for RD-Agent."""

    FORBIDDEN_PATTERNS = [
        (r"future.*look.*ahead", "Future function: using future data"),
        (r"shift\(", "Shift function: potential look-ahead bias"),
        (r"delay\(", "Delay function: potential data leakage"),
        (r"Ts_.*\(.*\(.*dt\)", "Nested dt: potential future information"),
    ]

    TRADING_RULES = {
        "max_position_size": 0.3,
        "max_industry_exposure": 0.3,
        "max_single_stock": 0.1,
        "min_liquidity_ratio": 0.05,
    }

    RISK_LIMITS = {
        "max_leverage": 1.0,
        "max_drawdown": 0.15,
        "min_sharpe": 0.5,
        "min_ic": 0.02,
    }

    def check_formula(self, formula: str) -> ConstraintResult:
        """Check if formula violates any constraints."""
        violations = []
        warnings = []

        for pattern, description in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, formula, re.IGNORECASE):
                violations.append(ConstraintViolation(
                    constraint_type=ConstraintType.FORBIDDEN_FUNCTION.value,
                    description=description,
                    severity=ViolationSeverity.CRITICAL,
                    suggested_fix="Use only past and current data",
                ))

        return ConstraintResult(
            is_allowed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
        )

    def check_trading_rules(
        self,
        position_size: float | None = None,
        industry_exposure: float | None = None,
        single_stock: float | None = None,
    ) -> ConstraintResult:
        """Check trading rule constraints."""
        violations = []

        if position_size is not None and position_size > self.TRADING_RULES["max_position_size"]:
            violations.append(ConstraintViolation(
                constraint_type=ConstraintType.TRADING_RULE.value,
                description=f"Position size {position_size:.1%} exceeds max {self.TRADING_RULES['max_position_size']:.1%}",
                severity=ViolationSeverity.HIGH,
                suggested_fix="Reduce position size",
            ))

        if industry_exposure is not None and industry_exposure > self.TRADING_RULES["max_industry_exposure"]:
            violations.append(ConstraintViolation(
                constraint_type=ConstraintType.TRADING_RULE.value,
                description=f"Industry exposure {industry_exposure:.1%} exceeds max {self.TRADING_RULES['max_industry_exposure']:.1%}",
                severity=ViolationSeverity.HIGH,
                suggested_fix="Diversify across industries",
            ))

        if single_stock is not None and single_stock > self.TRADING_RULES["max_single_stock"]:
            violations.append(ConstraintViolation(
                constraint_type=ConstraintType.TRADING_RULE.value,
                description=f"Single stock {single_stock:.1%} exceeds max {self.TRADING_RULES['max_single_stock']:.1%}",
                severity=ViolationSeverity.MEDIUM,
                suggested_fix="Reduce concentration",
            ))

        return ConstraintResult(
            is_allowed=len(violations) == 0,
            violations=violations,
            warnings=[],
        )

    def check_risk_limits(
        self,
        leverage: float | None = None,
        drawdown: float | None = None,
        sharpe: float | None = None,
        ic: float | None = None,
    ) -> ConstraintResult:
        """Check risk limit constraints."""
        violations = []

        if leverage is not None and leverage > self.RISK_LIMITS["max_leverage"]:
            violations.append(ConstraintViolation(
                constraint_type=ConstraintType.RISK_LIMIT.value,
                description=f"Leverage {leverage:.2f}x exceeds max {self.RISK_LIMITS['max_leverage']:.2f}x",
                severity=ViolationSeverity.CRITICAL,
            ))

        if drawdown is not None and drawdown > self.RISK_LIMITS["max_drawdown"]:
            violations.append(ConstraintViolation(
                constraint_type=ConstraintType.RISK_LIMIT.value,
                description=f"Drawdown {drawdown:.1%} exceeds max {self.RISK_LIMITS['max_drawdown']:.1%}",
                severity=ViolationSeverity.HIGH,
            ))

        if sharpe is not None and sharpe < self.RISK_LIMITS["min_sharpe"]:
            violations.append(ConstraintViolation(
                constraint_type=ConstraintType.RISK_LIMIT.value,
                description=f"Sharpe {sharpe:.2f} below min {self.RISK_LIMITS['min_sharpe']:.2f}",
                severity=ViolationSeverity.MEDIUM,
            ))

        if ic is not None and abs(ic) < self.RISK_LIMITS["min_ic"]:
            violations.append(ConstraintViolation(
                constraint_type=ConstraintType.RISK_LIMIT.value,
                description=f"IC {ic:.4f} below min {self.RISK_LIMITS['min_ic']:.4f}",
                severity=ViolationSeverity.LOW,
            ))

        return ConstraintResult(
            is_allowed=len(violations) == 0,
            violations=violations,
            warnings=[],
        )


class AutopilotCircuitBreaker:
    """Circuit breaker for autopilot to prevent continuous failures."""

    MAX_FAILURES = 3
    COOLDOWN_MINUTES = 60

    def __init__(self):
        self._failure_count = 0
        self._last_failure_time: datetime | None = None
        self._is_open = False

    def record_failure(self) -> None:
        """Record a failed attempt."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._failure_count >= self.MAX_FAILURES:
            self._is_open = True
            logger.warning(
                f"CIRCUIT OPEN: {self._failure_count} consecutive failures. "
                f"Autopilot entering sleep mode for {self.COOLDOWN_MINUTES} minutes."
            )

    def record_success(self) -> None:
        """Record a successful attempt."""
        self._failure_count = 0
        self._is_open = False
        logger.info("Circuit breaker reset: success recorded")

    def can_execute(self) -> tuple[bool, str]:
        """Check if execution is allowed."""
        if not self._is_open:
            return True, "ok"

        if self._last_failure_time:
            elapsed = datetime.now() - self._last_failure_time
            if elapsed > timedelta(minutes=self.COOLDOWN_MINUTES):
                logger.info("Circuit breaker: attempting reset after cooldown")
                self._failure_count = 0
                self._is_open = False
                return True, "cooldown_elapsed"

        return False, f"circuit_open:{self._failure_count}"

    def get_status(self) -> dict[str, Any]:
        """Get circuit breaker status."""
        can_exec, reason = self.can_execute()
        return {
            "is_open": self._is_open,
            "failure_count": self._failure_count,
            "can_execute": can_exec,
            "reason": reason,
            "cooldown_minutes": self.COOLDOWN_MINUTES,
        }


_constraints: NegativeConstraints | None = None
_circuit_breaker: AutopilotCircuitBreaker | None = None


def get_negative_constraints() -> NegativeConstraints:
    """Get the global negative constraints library."""
    global _constraints
    if _constraints is None:
        _constraints = NegativeConstraints()
    return _constraints


def get_circuit_breaker() -> AutopilotCircuitBreaker:
    """Get the global circuit breaker."""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = AutopilotCircuitBreaker()
    return _circuit_breaker
